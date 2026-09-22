from django.db import models
from accounts.models import User
from utils import SoftDeleteMixin


class Equipment(SoftDeleteMixin, models.Model):
    TYPE_CHOICES = (
        ('paddle', 'Paddle'),
        ('ball', 'Ball'),
        ('net', 'Net'),
        ('shoes', 'Shoes'),
        ('other', 'Other'),
    )
    
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    )
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, null=True)
    model_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Model')
    description = models.TextField(blank=True, null=True)
    storage_location = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Inventory
    quantity_total = models.PositiveIntegerField(default=1)
    quantity_available = models.PositiveIntegerField(default=1)
    quantity_reserved = models.PositiveIntegerField(default=0)
    
    # Pricing
    rental_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    purchase_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Status
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    is_active = models.BooleanField(default=True)
    
    # Images
    image = models.ImageField(upload_to='equipment/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'equipment'
        ordering = ['type', 'name']
        verbose_name_plural = 'Equipment'
        indexes = [
            models.Index(fields=['type', 'is_active']),
            models.Index(fields=['condition', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.type}) - Qty: {self.quantity_available}"
    
    def is_in_stock(self):
        return self.quantity_available > 0


class EquipmentRental(models.Model):
    STATUS_CHOICES = (
        ('reserved', 'Reserved'),
        ('rented', 'Rented'),
        ('returned', 'Returned'),
        ('damaged', 'Damaged/Lost'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='rentals')
    rented_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipment_rentals')
    reserved_date = models.DateField()
    quantity = models.PositiveIntegerField(default=1)

    # Rental period
    rented_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reserved')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    rental_fee = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Condition check
    condition_out = models.CharField(max_length=20, choices=Equipment.CONDITION_CHOICES, blank=True, null=True)
    condition_in = models.CharField(max_length=20, choices=Equipment.CONDITION_CHOICES, blank=True, null=True)
    
    # Staff
    checked_out_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='checkouts')
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='checkins')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_rentals')
    confirmed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'equipment_rentals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['equipment', 'status']),
            models.Index(fields=['rented_by', 'status']),
            models.Index(fields=['reserved_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.equipment.name} rented by {self.rented_by.username}"


class RentalPayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    METHOD_CHOICES = (
        ('gcash', 'GCash'),
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
    )

    rental = models.OneToOneField(EquipmentRental, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, blank=True, null=True)

    # For GCash payments
    gcash_reference = models.CharField(max_length=100, blank=True, null=True)
    gcash_proof_image = models.ImageField(upload_to='payments/gcash/rentals/', blank=True, null=True)

    # For cash payments
    cash_received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rental_cash_payments_received')
    cash_received_at = models.DateTimeField(null=True, blank=True)

    # Transaction details
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    payment_notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rental_payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.rental.equipment.name} - ₱{self.amount}"


class RentalPaymentLog(models.Model):
    payment = models.ForeignKey(RentalPayment, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)
    details = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rental_payment_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.payment.id} - {self.action}"


class EquipmentMaintenance(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_date = models.DateField()
    description = models.TextField()
    performed_by = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    next_maintenance_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'equipment_maintenance'
        ordering = ['-maintenance_date']

    def __str__(self):
        return f"Maintenance for {self.equipment.name} on {self.maintenance_date}"
