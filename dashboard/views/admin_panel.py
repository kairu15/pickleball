"""Staff/admin management screens (contact inbox, moderation).

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import admin_required
from accounts.models import User
from dashboard.models import ContactMessage
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from notifications.models import Notification


# Deprecated testimonial views - replaced by rating system
# Kept for reference but no longer used in URLs
@login_required
@admin_required
def contact_messages_view(request):
    """Admin view to display all contact messages"""
    
    messages_list = ContactMessage.objects.all().order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        messages_list = messages_list.filter(status=status_filter)
    
    # Count unread messages
    unread_count = ContactMessage.objects.filter(is_read=False).count()
    
    return render(request, 'admin/contact/contact_messages.html', {
        'messages': messages_list,
        'unread_count': unread_count,
        'status_filter': status_filter,
    })


@login_required
@admin_required
def contact_message_detail_view(request, message_id):
    """Admin view to view and reply to a specific contact message"""
    
    message = get_object_or_404(ContactMessage, id=message_id)
    
    # Mark as read when viewed
    if not message.is_read:
        message.is_read = True
        message.status = 'read'
        message.save()
    
    if request.method == 'POST':
        reply_text = request.POST.get('reply')
        action = request.POST.get('action')
        
        if action == 'reply' and reply_text:
            # Save the reply
            message.admin_reply = reply_text
            message.replied_by = request.user
            message.replied_at = timezone.now()
            message.status = 'replied'
            message.save()
            
            # Find the user by email and create a notification
            try:
                user = User.objects.get(email=message.email)
                Notification.objects.create(
                    user=user,
                    message=f"Admin replied to your message: {message.get_subject_display()}",
                    notification_type='success'
                )
            except User.DoesNotExist:
                # User doesn't exist, skip notification
                pass
            
            # Send email to the sender
            try:
                send_mail(
                    f'Re: {message.get_subject_display()} - PickleSphere',
                    f'Hi {message.name},\n\nThank you for contacting us. Here is our reply:\n\n{reply_text}\n\nBest regards,\nPickleSphere Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [message.email],
                    fail_silently=True
                )
                messages.success(request, 'Reply sent successfully!')
            except Exception:
                messages.success(request, 'Reply saved successfully!')
            
            return redirect('super_admin_contact_messages')
        
        elif action == 'close':
            message.status = 'closed'
            message.save()
            messages.success(request, 'Message closed.')
            return redirect('super_admin_contact_messages')
    
    return render(request, 'admin/contact/contact_message_detail.html', {
        'message': message,
    })


@login_required
def admin_reject_testimonial_view(request, testimonial_id):
    """DEPRECATED: Testimonials replaced by rating system"""
    messages.info(request, 'Testimonials have been replaced by our new rating system.')
    return redirect('super_admin_homepage')
