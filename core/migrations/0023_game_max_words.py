# Generated by Django 2.2.10 on 2020-04-10 22:28

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_auto_20200410_1904'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='max_words',
            field=models.IntegerField(default=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
