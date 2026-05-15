from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0004_memorial_warriors_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_status",
            field=models.CharField(
                choices=[("pending", "Ожидает оплаты"), ("paid", "Оплачен")],
                default="pending",
                max_length=16,
            ),
        ),
    ]
