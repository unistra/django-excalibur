from django.contrib import admin
from .models import Configuration
from django import forms


class ConfigurationAdminForm(forms.ModelForm):

    class Meta:
        model = Configuration
        exclude = []

    def __init__(self, *args, **kwargs):
        super(ConfigurationAdminForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['name'].widget.attrs['readonly'] = True
            self.fields['configuration'].widget = forms.Textarea(
                attrs={'cols': 80, 'rows': 40})


class ConfigurationAdmin(admin.ModelAdmin):
    form = ConfigurationAdminForm
    list_display = ('name',)
    list_filter = ('name', )
    ordering = ('name',)


admin.site.register(Configuration, ConfigurationAdmin)
