from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0003_service_holiday_types"),
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
                    ("parents_saturday", "Поминальные работы в родительскую субботу"),
                    ("pascha_care", "Поминальные работы к Пасхе"),
                    ("memorial_warriors", "Поминовение усопших воинов"),
                    ("trinity_care", "Поминальные работы к Троице"),
                    ("victory_day_care", "Поминальные работы к 9 мая"),
                    ("memorial_day_care", "Поминальные работы ко Дню памяти"),
                ],
                max_length=32,
                unique=True,
            ),
        ),
    ]
