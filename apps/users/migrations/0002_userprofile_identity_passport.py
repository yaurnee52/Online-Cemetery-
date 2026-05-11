# Generated manually for identity fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="last_name",
            field=models.CharField(blank=True, max_length=64, verbose_name="Фамилия"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="first_name",
            field=models.CharField(blank=True, max_length=64, verbose_name="Имя"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="patronymic",
            field=models.CharField(blank=True, max_length=64, verbose_name="Отчество"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="no_patronymic",
            field=models.BooleanField(default=False, verbose_name="Нет отчества"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="passport_series",
            field=models.CharField(blank=True, max_length=8, verbose_name="Серия паспорта"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="passport_number",
            field=models.CharField(blank=True, max_length=6, verbose_name="Номер паспорта"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="poa_city",
            field=models.CharField(
                blank=True,
                default="г. Москва",
                max_length=128,
                verbose_name="Город для доверенности",
            ),
        ),
    ]
