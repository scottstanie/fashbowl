# Generated by Django 2.2.10 on 2020-04-10 16:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_game_max_word_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='game',
            name='blue_giver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='blue_giver', to='core.Player'),
        ),
        migrations.AlterField(
            model_name='game',
            name='red_giver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='red_giver', to='core.Player'),
        ),
    ]