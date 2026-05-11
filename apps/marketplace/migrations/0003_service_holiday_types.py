from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0002_alter_donation_status_alter_order_status_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicetype",
            name="code",
            field=models.CharField(
                choices=[
                    ("cleaning", "Уборка участка"),
                    ("fence_painting", "Покраска ограждений"),
                    ("inspection", "Проверка состояния"),
                    ("radonitsa_remote", "Дистанционная Радоница"),
                    ("parents_saturday", "Уход в родительскую субботу"),
                    ("pascha_care", "Уход к Пасхе"),
                    ("trinity_care", "Уход к Троице"),
                    ("victory_day_care", "Уход к 9 мая"),
                    ("memorial_day_care", "Уход ко Дню памяти"),
                ],
                max_length=32,
                unique=True,
            ),
        ),
    ]
