"""
tenants/models.py
Tenant model for GetCore multi-tenant ERP.

Each tenant is a distinct business client with their own:
  - Users, Products, Sales, Settings, Reports
  - Accessed via example.com/<tenant_slug>/
"""

from django.db import models


class Tenant(models.Model):
    """
    A single business client (tenant).
    Identified by a unique URL-safe slug that forms the access key.
    """

    PLAN_CHOICES = [
        ('trial',      'Free Trial (14 days)'),
        ('starter',    'Starter'),
        ('business',   'Business'),
        ('enterprise', 'Enterprise'),
    ]
    
    BUSINESS_TYPE_CHOICES = [
        # Food & Beverage
        ('bar', 'Bar'),
        ('restaurant', 'Restaurant'),
        ('bar_and_restaurant', 'Bar & Restaurant'),
        ('cafe', 'Café'),
        ('fast_food', 'Fast Food'),
        ('bakery', 'Bakery'),
        ('butchery', 'Butchery'),
        ('nyama_choma', 'Nyama Choma Joint'),
        ('juice_bar', 'Juice Bar'),
        ('catering', 'Catering Services'),

        # Alcohol & Tobacco
        ('wines_and_spirits', 'Wines & Spirits'),
        ('liquor_store', 'Liquor Store'),
        
        # Retail Shops
        ('grocery', 'Grocery'),
        ('supermarket', 'Supermarket'),
        ('wholesale_shop', 'Wholesale Shop'),
        ('kiosk', 'Kiosk'),
        ('general_store', 'General Store'),

        # Health & Beauty
        ('pharmacy', 'Pharmacy'),
        ('chemist', 'Chemist'),
        ('salon', 'Salon'),
        ('barbershop', 'Barbershop'),
        ('spa', 'Spa'),
        ('cosmetics', 'Cosmetics Shop'),

        # Fashion & Apparel
        ('clothing', 'Clothing'),
        ('boutique', 'Boutique'),
        ('shoe_store', 'Shoe Store'),
        ('tailor', 'Tailor'),

        # Electronics & Tech
        ('electronics', 'Electronics'),
        ('phone_shop', 'Phone Shop'),
        ('computer_shop', 'Computer Shop'),
        ('cyber_cafe', 'Cyber Café'),
        ('repair_shop', 'Repair Shop'),

        # Agriculture & Livestock
        ('agrovet', 'Agrovet'),
        ('farm', 'Farm'),
        ('dairy', 'Dairy Shop'),
        ('poultry', 'Poultry Business'),

        # Hardware & Construction
        ('hardware', 'Hardware Store'),
        ('timber_yard', 'Timber Yard'),
        ('paint_shop', 'Paint Shop'),

        # Transport & Automotive
        ('car_dealership', 'Car Dealership'),
        ('garage', 'Garage'),
        ('car_wash', 'Car Wash'),
        ('spare_parts', 'Spare Parts Shop'),
    ]
    name = models.CharField(
        max_length=200,
        help_text='Business / client name e.g. "Kamau Agrovet Nakuru"'
    )
    business_type = models.CharField(
        max_length=200,
        choices=BUSINESS_TYPE_CHOICES,
        null=True,
        help_text='Select the type of business'
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
    )
    # Internal reference for platform admin
    reference_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
    )

    # ── Contact ────────────────────────────────────────────────────────────
    owner_name  = models.CharField(max_length=150, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)

    # ── Subscription ───────────────────────────────────────────────────────
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive tenants cannot log in.'
    )
    trial_ends_on = models.DateField(null=True, blank=True)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    load_default_categories = models.BooleanField(
        default=False
    )
    load_default_products = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return f'{self.name} ({self.slug})'

    def save(self, *args, **kwargs):
        # Auto-generate reference code on first save
        if not self.reference_code:
            count = Tenant.objects.count() + 1
            self.reference_code = f'GC-{count:05d}'
            self.slug = f'{self.name.lower().replace(" ", "-")}-{self.reference_code.lower()}'
        super().save(*args, **kwargs)

    @property
    def access_url_path(self):
        return f'/{self.slug}/'
