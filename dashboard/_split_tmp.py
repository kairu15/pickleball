"""Throwaway code-motion helper: splits dashboard/views.py + dashboard/cms_views.py
into the feature-grouped dashboard/views/ package. Deleted before handoff.
"""
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STMT_RE = re.compile(r"^(def |class |@|import |from |[A-Za-z_][A-Za-z0-9_]*\s*=[^=])")

SHARED_NAMES = (
    'STATIC_CONTACT_PHONE',
    'STATIC_CONTACT_EMAIL',
    '_get_contact_info',
    '_get_contact_page_data',
    '_log_version',
)

MODULES = [
    ('shared', 'Shared imports, constants and cross-cutting helpers.'),
    ('home', 'Dashboard home / index / role redirects.'),
    ('public_pages', 'Public marketing pages (courts, pricing, about, contact, legal, FAQ).'),
    ('users', 'User-facing dashboard, messages and ratings.'),
    ('analytics', 'Super-admin reports, revenue analytics, exports and cache monitor.'),
    ('admin_panel', 'Staff/admin management screens (contact inbox, moderation).'),
    ('cms_homepage', 'Home page CMS (sections, testimonials, amenities, gallery).'),
    ('cms_pricing', 'Pricing page CMS.'),
    ('cms_about', 'About page CMS.'),
    ('cms_contact', 'Contact page CMS.'),
    ('cms_pages', 'Courts / tournaments / equipment page CMS.'),
    ('cms_content', 'FAQ, terms, privacy, media library, content versions, hero CMS.'),
    ('cms_navigation', 'Branding, top bar, navbar, footer and social media CMS.'),
    ('site_settings', 'Site settings, partners, announcements and maintenance mode.'),
    ('design', 'Global design system: design tokens, buttons, cards, scroll-to-top.'),
]

CMS_VIEW_MODULES = ('cms_pages', 'cms_content', 'cms_navigation', 'design')


def read(path):
    return io.open(os.path.join(ROOT, path), encoding='utf-8').read()


def split_blocks(text):
    """Split a module source into top-level blocks.

    Decorator runs are merged into the ``def`` they belong to and comments
    directly above a statement stay attached to it, so every block is either a
    complete (decorators + signature + body) function or a top-level statement.
    """
    lines = text.split('\n')
    entries = []
    for i, line in enumerate(lines):
        if STMT_RE.match(line):
            j = i - 1
            while j >= 0:
                stripped = lines[j]
                if not stripped.strip() or stripped.startswith('#'):
                    j -= 1
                    continue
                break
            start = j + 1
            while not lines[start].strip():
                start += 1
            entries.append({'start': start, 'stmt_line': i, 'decorator': line.startswith('@')})

    starts = []
    pending = None
    for entry in entries:
        if entry['decorator']:
            if pending is None:
                pending = entry['start']
            continue
        starts.append((pending if pending is not None else entry['start'], entry['stmt_line']))
        pending = None
    if pending is not None:
        starts.append((pending, len(lines) - 1))

    blocks = []
    for idx, (start, stmt) in enumerate(starts):
        end = starts[idx + 1][0] - 1 if idx + 1 < len(starts) else len(lines) - 1
        while end > stmt and not lines[end].strip():
            end -= 1
        blocks.append({'start': start, 'end': end, 'stmt': lines[stmt]})
    return lines, blocks


def block_text(lines, block):
    return '\n'.join(lines[block['start']:block['end'] + 1])


def name_of(block):
    stmt = block['stmt']
    m = re.match(r'def ([A-Za-z_][A-Za-z0-9_]*)\(', stmt)
    if m:
        return m.group(1)
    m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=', stmt)
    if m:
        return m.group(1)
    return None


def used_names(text):
    names = set()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return names


def import_map(text):
    """Imported name -> (group key, import item) for every module-level import."""
    mapping = {}
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                mapping[alias.asname or alias.name.split('.')[0]] = ('import', alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if node.level:
                module = 'dashboard.' + module
            for alias in node.names:
                name = alias.asname or alias.name
                item = alias.name if not alias.asname else '%s as %s' % (alias.name, alias.asname)
                mapping[name] = ('from ' + module, item)
    return mapping


# Feature grouping: every top-level callable of the two legacy modules.
ASSIGNMENT = {
    # ---- dashboard/views.py ----
    'home_view': 'home',
    'dashboard_view': 'home',
    'staff_dashboard_view': 'home',
    'all_courts_view': 'public_pages',
    'court_view_view': 'public_pages',
    'pricing_view': 'public_pages',
    'about_view': 'public_pages',
    'contact_view': 'public_pages',
    'privacy_policy_view': 'public_pages',
    'terms_of_service_view': 'public_pages',
    'faq_view': 'public_pages',
    'user_dashboard_view': 'users',
    'user_messages_view': 'users',
    'submit_rating_view': 'users',
    'check_pending_rating_view': 'users',
    'admin_dashboard_view': 'analytics',
    'dashboard_export_view': 'analytics',
    'cache_monitor_view': 'analytics',
    'rating_list_view': 'analytics',
    'contact_messages_view': 'admin_panel',
    'contact_message_detail_view': 'admin_panel',
    'admin_reject_testimonial_view': 'admin_panel',
    'homepage_management': 'cms_homepage',
    'homepage_edit_content': 'cms_homepage',
    'populate_homepage_content': 'cms_homepage',
    'toggle_featured_rating': 'cms_homepage',
    'homepage_edit_testimonial': 'cms_homepage',
    'homepage_edit_amenity': 'cms_homepage',
    'homepage_edit_gallery': 'cms_homepage',
    'homepage_delete_testimonial': 'cms_homepage',
    'homepage_delete_amenity': 'cms_homepage',
    'homepage_delete_gallery': 'cms_homepage',
    'pricing_management': 'cms_pricing',
    'pricing_edit_content': 'cms_pricing',
    'pricing_delete_content': 'cms_pricing',
    'pricing_edit_tier': 'cms_pricing',
    'pricing_delete_tier': 'cms_pricing',
    'pricing_edit_faq': 'cms_pricing',
    'pricing_delete_faq': 'cms_pricing',
    'about_management': 'cms_about',
    'about_edit_content': 'cms_about',
    'about_delete_content': 'cms_about',
    'about_edit_milestone': 'cms_about',
    'about_delete_milestone': 'cms_about',
    'about_edit_team_member': 'cms_about',
    'about_delete_team_member': 'cms_about',
    'about_edit_facility': 'cms_about',
    'about_delete_facility': 'cms_about',
    'about_edit_why_item': 'cms_about',
    'about_delete_why_item': 'cms_about',
    'about_add_gallery_image': 'cms_about',
    'about_delete_gallery_image': 'cms_about',
    'contact_management': 'cms_contact',
    'contact_edit_content': 'cms_contact',
    'contact_delete_content': 'cms_contact',
    'contact_edit_info': 'cms_contact',
    'contact_edit_business_hour': 'cms_contact',
    'contact_delete_business_hour': 'cms_contact',
    'contact_edit_faq': 'cms_contact',
    'contact_delete_faq': 'cms_contact',
    'contact_edit_social_link': 'cms_contact',
    'contact_delete_social_link': 'cms_contact',
    # ---- dashboard/cms_views.py ----
    'courts_page_settings': 'cms_pages',
    'courts_featured_add': 'cms_pages',
    'courts_featured_edit': 'cms_pages',
    'courts_featured_delete': 'cms_pages',
    'tournaments_page_settings': 'cms_pages',
    'tournament_category_add': 'cms_pages',
    'tournament_category_edit': 'cms_pages',
    'tournament_category_delete': 'cms_pages',
    'tournament_featured_add': 'cms_pages',
    'tournament_featured_edit': 'cms_pages',
    'tournament_featured_delete': 'cms_pages',
    'tournament_announcement_add': 'cms_pages',
    'tournament_announcement_edit': 'cms_pages',
    'tournament_announcement_delete': 'cms_pages',
    'equipment_page_settings': 'cms_pages',
    'equipment_category_add': 'cms_pages',
    'equipment_category_edit': 'cms_pages',
    'equipment_category_delete': 'cms_pages',
    'equipment_featured_add': 'cms_pages',
    'equipment_featured_edit': 'cms_pages',
    'equipment_featured_delete': 'cms_pages',
    'content_version_list': 'cms_content',
    'faq_cms_settings': 'cms_content',
    'faq_category_add': 'cms_content',
    'faq_category_edit': 'cms_content',
    'faq_category_delete': 'cms_content',
    'faq_item_add': 'cms_content',
    'faq_item_edit': 'cms_content',
    'faq_item_delete': 'cms_content',
    'terms_cms_settings': 'cms_content',
    'terms_section_add': 'cms_content',
    'terms_section_edit': 'cms_content',
    'terms_section_delete': 'cms_content',
    'privacy_cms_settings': 'cms_content',
    'privacy_section_add': 'cms_content',
    'privacy_section_edit': 'cms_content',
    'privacy_section_delete': 'cms_content',
    'media_library_view': 'cms_content',
    'media_library_upload': 'cms_content',
    'media_library_edit': 'cms_content',
    'media_library_delete': 'cms_content',
    'hero_section_settings': 'cms_content',
    'hero_section_preview': 'cms_content',
    'site_branding_settings': 'cms_navigation',
    'site_branding_remove_logo': 'cms_navigation',
    'site_branding_restore_defaults': 'cms_navigation',
    'topbar_settings': 'cms_navigation',
    'navbar_settings': 'cms_navigation',
    'navbar_menu_item_add': 'cms_navigation',
    'navbar_menu_item_edit': 'cms_navigation',
    'navbar_menu_item_delete': 'cms_navigation',
    'footer_settings': 'cms_navigation',
    'footer_quick_link_add': 'cms_navigation',
    'footer_quick_link_edit': 'cms_navigation',
    'footer_quick_link_delete': 'cms_navigation',
    'social_media_settings': 'cms_navigation',
    'social_platform_edit': 'cms_navigation',
    'maintenance_mode_settings': 'site_settings',
    'site_settings_view': 'site_settings',
    'partner_add': 'site_settings',
    'partner_edit': 'site_settings',
    'partner_delete': 'site_settings',
    'announcement_add': 'site_settings',
    'announcement_edit': 'site_settings',
    'announcement_delete': 'site_settings',
    'global_design_settings': 'design',
    'button_style_settings': 'design',
    'card_style_settings': 'design',
    'scroll_to_top_settings': 'design',
}


def build():
    sources = {}
    for path in ('dashboard/views.py', 'dashboard/cms_views.py'):
        text = read(path)
        lines, blocks = split_blocks(text)
        sources[path] = {'text': text, 'lines': lines, 'blocks': blocks, 'globals': import_map(text)}

    module_blocks = {name: [] for name, _ in MODULES}
    module_order = {name: idx for idx, (name, _) in enumerate(MODULES)}
    seen = set()
    for path in ('dashboard/views.py', 'dashboard/cms_views.py'):
        for block in sources[path]['blocks']:
            if block['stmt'].startswith(('import ', 'from ')):
                continue
            name = name_of(block)
            if name is None:
                if block['stmt'].strip():
                    print('UNCLASSIFIED BLOCK in %s line %d: %r' % (path, block['start'] + 1, block['stmt'][:60]))
                continue
            if name in SHARED_NAMES:
                module_blocks['shared'].append((path, block))
            elif name in ASSIGNMENT:
                module_blocks[ASSIGNMENT[name]].append((path, block))
            elif block['stmt'].startswith('def '):
                print('UNASSIGNED FUNCTION %s (%s line %d)' % (name, path, block['start'] + 1))
            else:
                print('SKIPPED TOP-LEVEL ASSIGNMENT %s (%s line %d)' % (name, path, block['start'] + 1))
            if name:
                seen.add(name)

    missing = sorted(set(ASSIGNMENT) - seen)
    if missing:
        print('ASSIGNMENT ENTRIES WITH NO SOURCE BLOCK:', missing)

    merged_globals = {}
    for path in ('dashboard/views.py', 'dashboard/cms_views.py'):
        merged_globals.update(sources[path]['globals'])

    def local_imports(text):
        names = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                names.update(a.asname or a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update(a.asname or a.name for a in node.names)
        return names

    written = {}
    for name, doc in MODULES:
        chunks, defined, needed, local_names = [], set(), set(), set()
        for path, block in module_blocks[name]:
            text = block_text(sources[path]['lines'], block)
            text = text.replace('from .models import', 'from dashboard.models import')
            text = text.replace('from .cache_utils import', 'from dashboard.cache_utils import')
            chunks.append(text)
            bname = name_of(block)
            if bname:
                defined.add(bname)
            local_names |= local_imports(text)
            needed |= used_names(text)
        needed -= defined
        needed -= local_names
        groups = {}
        for gname in sorted(needed & set(merged_globals)):
            key, item = merged_globals[gname]
            groups.setdefault(key, []).append(item)
        for sname in sorted((needed & set(SHARED_NAMES)) - defined):
            if name != 'shared':
                groups.setdefault('from dashboard.views.shared', []).append(sname)
        cross = sorted(needed & set(ASSIGNMENT))
        for cname in cross:
            if ASSIGNMENT[cname] != name:
                groups.setdefault('from dashboard.views.%s' % ASSIGNMENT[cname], []).append(cname)
        if cross:
            print('CROSS-MODULE references in %s: %s' % (name, cross))
        lines = []
        for key in sorted(groups):
            items = sorted(set(groups[key]))
            if key == 'import':
                lines.extend('import %s' % item for item in items)
            else:
                lines.append('%s import %s' % (key, ', '.join(items)))
        header = '"""%s\n\nMoved verbatim out of the legacy ``dashboard.views`` /\n``dashboard.cms_views`` modules (pure code motion).\n"""\n' % doc
        body = header
        if lines:
            body += '\n' + '\n'.join(sorted(set(lines))) + '\n'
        body += '\n\n' + '\n\n\n'.join(chunks) + '\n'
        written[name] = body
    return written, module_blocks, merged_globals


def write_package(written, target_dir):
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
    for name in written:
        with io.open(os.path.join(target_dir, name + '.py'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(written[name])


def public_names(paths=('dashboard/views.py', 'dashboard/cms_views.py')):
    names = []
    for path in paths:
        text = io.open(os.path.join(ROOT, path), encoding='utf-8').read()
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                names.append(node.name)
    return names


def report(written):
    print('%-16s %6s  %s' % ('MODULE', 'LINES', 'PUBLIC CALLABLES'))
    total = 0
    for name, _ in MODULES:
        body = written[name]
        count = len(re.findall(r'^def ', body, re.M))
        total += count
        print('%-16s %6d  %d' % (name, body.count('\n'), count))
    print('%-16s %6s  %d' % ('TOTAL', '', total))
    print('legacy views.py + cms_views.py public defs:', len(public_names()))


def wrap(names, prefix='    ', width=76):
    out, line = [], prefix
    for name in names:
        piece = name + ', '
        if len(line) + len(piece) > width and line.strip():
            out.append(line.rstrip())
            line = prefix
        line += piece
    if line.strip():
        out.append(line.rstrip())
    return out


def import_line(module, names, wrap_it):
    if not wrap_it or len(', '.join(names)) < 50:
        joined = ', '.join(names)
        if len('from dashboard.views.%s import %s' % (module, joined)) <= 79:
            return ['from dashboard.views.%s import %s' % (module, joined)]
    lines = ['from dashboard.views.%s import (' % module]
    lines += wrap(names)
    lines.append(')')
    return lines


def build_init():
    body = [
        '"""Feature-grouped dashboard views (split out of the former monolithic',
        '``dashboard.views`` and ``dashboard.cms_views`` modules).',
        '',
        'Every previously public view callable is re-exported here so that',
        '``from dashboard.views import <name>``, ``from . import views`` plus',
        '``views.<name>`` in the URL modules, and ``dashboard.cms_views.<name>``',
        'all keep resolving exactly as before.',
        '',
        'Shared constants/helpers live in :mod:`dashboard.views.shared` and are',
        'imported directly by the feature modules (never through this package',
        '``__init__``) so no import cycle can form.',
        '"""',
        '',
    ]
    all_names = []
    for module, _ in MODULES:
        names = [n for n, m in ASSIGNMENT.items() if m == module]
        if not names:
            continue
        all_names.extend(names)
        body.append('# --- %s ---' % module)
        body += import_line(module, names, True)
        body.append('')
    body.append('__all__ = [')
    body += wrap(sorted(all_names))
    body.append(']')
    return '\n'.join(body) + '\n', sorted(all_names)


def main():
    written, blocks, _globals = build()
    target = os.path.join(ROOT, 'dashboard', 'views')
    write_package(written, target)
    init_body, pkg_names = build_init()
    with io.open(os.path.join(target, '__init__.py'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(init_body)
    legacy = sorted(public_names())
    print('package re-exports : %d' % len(pkg_names))
    print('legacy public defs : %d' % len(legacy))
    print('missing from package:', sorted(set(legacy) - set(pkg_names)))
    print('extra in package   :', sorted(set(pkg_names) - set(legacy)))
    mods = {m: [n for n, mod in ASSIGNMENT.items() if mod == m] for m, _ in MODULES}
    print('per-module counts  :', {m: len(v) for m, v in mods.items() if v})
    report(written)
    legacy_src = read('dashboard/views.py') + read('dashboard/cms_views.py')
    pkg_src = '\n'.join(written[m] for m, _ in MODULES)
    for token in ('@login_required', '@admin_required', '@super_admin_required',
                  '@user_required', '@staff_or_admin_required', '@cache_anon_page('):
        print('%-24s legacy=%d package=%d' % (token, legacy_src.count(token), pkg_src.count(token)))


def build_shim():
    """The ``dashboard/cms_views.py`` compatibility shim."""
    names = [n for n, m in ASSIGNMENT.items() if m in CMS_VIEW_MODULES]
    body = [
        '"""Backwards-compatible shim for the former ``dashboard/cms_views.py``.',
        '',
        'The CMS views now live in the feature-grouped :mod:`dashboard.views`',
        'package; this module re-exports every name it used to define so any',
        'existing ``from dashboard.cms_views import X`` / ``cms_views.X``',
        'reference keeps working unchanged.',
        '"""',
        '',
    ]
    for module in ('cms_content', 'cms_navigation', 'cms_pages', 'design'):
        mod_names = [n for n in names if ASSIGNMENT[n] == module]
        body += import_line(module, mod_names, True)
        body.append('')
    body.append('from dashboard.views.shared import _log_version  # noqa: F401')
    body.append('')
    body.append('__all__ = [')
    body += wrap(sorted(names))
    body.append(']')
    return '\n'.join(body) + '\n', sorted(names)


def verify():
    """Prove the package is byte-for-byte code motion of the legacy modules."""
    import glob
    dumps = {}
    for path in ('dashboard/views.py', 'dashboard/cms_views.py'):
        text = read(path)
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef):
                dumps[node.name] = ast.dump(node, include_attributes=False).replace(
                    "from .models", "from dashboard.models")
    seen = 0
    problems = []
    for fpath in sorted(glob.glob(os.path.join(ROOT, 'dashboard', 'views', '*.py'))):
        if os.path.basename(fpath) == '__init__.py':
            continue
        src = io.open(fpath, encoding='utf-8').read()
        for node in ast.parse(src).body:
            if not isinstance(node, ast.FunctionDef):
                continue
            seen += 1
            expected = dumps.get(node.name)
            if expected is None:
                problems.append('%s: %s not found in legacy modules' % (fpath, node.name))
                continue
            actual = ast.dump(node, include_attributes=False)
            if actual != expected:
                problems.append('%s: %s BODY/HEADER DIFFERS' % (fpath, node.name))
    print('functions compared : %d (legacy %d)' % (seen, len(dumps)))
    print('mismatches         : %s' % (problems or 'none'))
    return problems


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify()
    else:
        main()
