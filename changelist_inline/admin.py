import urllib

from django import forms
from django.forms.models import _get_foreign_key
from django.contrib import admin
from django.contrib.admin.options import InlineModelAdmin
from django.contrib.admin.templatetags.admin_static import static
from django.core.urlresolvers import reverse
from django.template.loader import select_template


class ChangeListInline(InlineModelAdmin):
    """
    Use an admin changelist for a ModelAdmin inline.
    """
    classes = []

    def __init__(self, parent_model, admin_site):
        super(ChangeListInline, self).__init__(parent_model, admin_site)

        if isinstance(self, admin.ModelAdmin):
            # don't continue if we're the hybrid modeladmin we've created below
            return

        self.context = None
        self.parent_obj = None
        self.fk = _get_foreign_key(parent_model, self.model,
                                   fk_name=self.fk_name)

        # Create a Modeldmin to be used to render the change list
        modeladmin_name = '{0}ModelAdmin'.format(self.__class__.__name__)
        modeladmin_attrs = {}
        # Inherit custom attributes defined on this instance, as well as
        # get_queryset()
        base_attrs = set(dir(ChangeListInline)) | {
            '_orig_formfield_overrides', 'admin_site', 'fk', 'parent_model',
            'parent_obj', 'opts', 'context'}
        custom_attrs = set(dir(self)) - base_attrs
        inherit = custom_attrs | {'get_queryset'}
        modeladmin_attrs = dict((a, getattr(self, a)) for a in inherit)
        ModelAdmin = type(modeladmin_name, (admin.ModelAdmin,),
                          modeladmin_attrs)
        self._modeladmin = ModelAdmin(self.model, admin_site)

    def get_fieldsets(self, request, obj=None, **kwargs):
        self.parent_obj = obj
        if not obj:
            return []

        # Allows us to do stuff with request before we're put inside the
        # AdminInlineFormSet helper class
        self.context = self.get_context(request, obj)

        return super(ChangeListInline, self).get_fieldsets(
            request, obj, **kwargs)

    def get_extra(self, request, obj=None, **kwargs):
        # There's no "add another" in this inline.
        return 0

    def get_add_url(self, obj, **kwargs):
        urlname = 'admin:{0.app_label}_{0.model_name}_add'
        url = reverse(urlname.format(self.model._meta))
        params = {
            self.fk.name: getattr(obj, self.fk.rel.field_name)
        }
        params.update(kwargs)
        return '?'.join((url, urllib.urlencode(params)))

    def get_queryset(self, request):
        qs = super(ChangeListInline, self).get_queryset(request)
        if not self.parent_obj:
            return qs.none()
        return qs.filter(**{self.fk.name: self.parent_obj})

    def get_context(self, request, obj=None, extra_context=None):
        # hijack the context from teh changelist_view template response
        response = self._modeladmin.changelist_view(request, extra_context)
        context = response.context_data
        context.update({
            'classes': ' '.join(self.classes),
            'add_url': self.get_add_url(obj)
        })
        return context

    def get_template(self):
        info = self.model._meta
        tpl = select_template((s.format(info) for s in (
            'admin/{0.app_label}/{0.model_name}/change_list_inline.html',
            'admin/{0.app_label}/change_list_inline.html',
            'admin/change_list_inline.html'
        )))
        return tpl.name
    template = property(get_template)

    @property
    def media(self):
        return forms.Media(
            css={'all': [
                static('changelist_inline/css/changelist_inline.css')
            ]},
            js=[
                'changelist_inline/js/changelist_inline.js'
            ]
        )
