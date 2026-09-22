"""Tests covering the escape-by-default changes for CMS-supplied values.

Two render paths used to bypass escaping entirely via ``|safe``:

* chart data injected into inline ``<script>`` blocks, and
* CMS design tokens injected into a ``<style>`` block.

Both are now routed through a sanitizer, so these tests pin the escaping
behaviour and prove a malicious value can no longer break out of its context.
"""

from django.test import SimpleTestCase, TestCase
from django.template import Context, Template

from dashboard.models import GlobalDesignSettings, sanitize_css_value
from dashboard.templatetags.dashboard_filters import to_json


class ToJsonFilterTests(SimpleTestCase):
    """The filter that replaces ``{{ value|safe }}`` in chart scripts."""

    def test_list_of_labels_serializes_as_json_array(self):
        self.assertEqual(to_json(['Jan', 'Feb']), '["Jan", "Feb"]')

    def test_numeric_list_serializes_without_quotes(self):
        self.assertEqual(to_json([1, 2, 3]), '[1, 2, 3]')

    def test_apostrophe_in_value_does_not_break_the_literal(self):
        # A Python repr would emit a single-quoted string and terminate early.
        self.assertEqual(to_json(["O'Brien's Court"]), '["O\'Brien\'s Court"]')

    def test_script_closing_tag_is_neutralised(self):
        # A court name containing </script> must not close the surrounding tag.
        rendered = to_json(['</script><script>alert(1)</script>'])
        self.assertNotIn('<', rendered)
        self.assertNotIn('>', rendered)
        self.assertIn('\\u003C', rendered)

    def test_ampersand_and_angle_brackets_are_escaped(self):
        rendered = to_json(['<b>Court & Co</b>'])
        for char in ('<', '>', '&'):
            self.assertNotIn(char, rendered)

    def test_pre_serialized_json_is_passed_through(self):
        self.assertEqual(to_json('[1, 2]'), '[1, 2]')

    def test_plain_string_is_json_encoded(self):
        self.assertEqual(to_json('hello'), '"hello"')

    def test_markup_is_rendered_unescaped_by_the_template_engine(self):
        # The whole point is a raw JS literal, so the filter must be marked
        # safe; otherwise autoescaping would mangle the JSON quotes.
        rendered = Template(
            '{% load dashboard_filters %}var d = {{ data|to_json }};'
        ).render(Context({'data': ['a', 'b']}))
        self.assertEqual(rendered, 'var d = ["a", "b"];')


class SanitizeCssValueTests(SimpleTestCase):
    def test_legitimate_values_are_untouched(self):
        for value in ('#3B7A8C', '16px', "'Inter', sans-serif",
                      '0 4px 16px rgba(0,0,0,0.08)', '5rem 0'):
            self.assertEqual(sanitize_css_value(value), value)

    def test_declaration_terminators_are_stripped(self):
        self.assertEqual(sanitize_css_value('red; color: blue'), 'red color: blue')

    def test_block_characters_are_stripped(self):
        self.assertEqual(sanitize_css_value('red} body { background: pink'),
                         'red body  background: pink')

    def test_comment_delimiters_are_stripped(self):
        self.assertEqual(sanitize_css_value('red /* x */ blue'), 'red  x  blue')

    def test_none_becomes_empty_string(self):
        self.assertEqual(sanitize_css_value(None), '')


class GlobalDesignSettingsCssTests(TestCase):
    def _design(self, **overrides):
        design = GlobalDesignSettings.objects.create()
        if overrides:
            for field, value in overrides.items():
                setattr(design, field, value)
        return design

    def test_defaults_still_render_a_valid_root_block(self):
        css = self._design().get_css_variables()
        self.assertTrue(css.startswith(':root {'))
        self.assertTrue(css.endswith('}'))
        self.assertIn('--primary-color: #3B7A8C;', css)
        self.assertIn('--primary-rgb: 59, 122, 140;', css)

    def test_injected_value_cannot_open_a_new_rule(self):
        css = self._design(primary_color='red; } body { display: none').get_css_variables()
        self.assertNotIn('}', css.replace(':root {', '', 1).rsplit('}', 1)[0])
        # The malicious declaration must not appear as its own rule.
        self.assertEqual(css.count('{'), 1)
        self.assertEqual(css.count('}'), 1)

    def test_malformed_hex_does_not_raise(self):
        # 'zzzzzz' is six characters but not hex; this used to raise ValueError.
        css = self._design(primary_color='zzzzzz').get_css_variables()
        self.assertIn('--primary-rgb: 59, 122, 140;', css)
