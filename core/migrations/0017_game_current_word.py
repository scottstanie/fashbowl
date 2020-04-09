# Generated by Django 2.2.10 on 2020-04-09 22:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_remove_game_current_word'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='current_word',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Word'),
        ),
    ]