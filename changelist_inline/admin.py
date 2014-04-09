import urllib
from collections import namedtuple

from django import forms
from django.contrib import admin
from django.contrib.admin.options import InlineModelAdmin
from django.contrib.admin.templatetags.admin_static import static
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.template.loader import select_template

GenericFK = namedtuple('GenericFK', ['ct_field', 'fk_field'])


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

        self.parent_obj = None
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

    def get_fk_field(self, request, obj, **kwargs):
        if not hasattr(self, '_fk'):
            formset = self.get_formset(request, obj, **kwargs)
            if issubclass(formset, BaseGenericInlineFormSet):
                self._fk = GenericFK(formset.ct_field, formset.ct_fk_field)
            else:
                self._fk = formset.fk
        return self._fk

    def get_fieldsets(self, request, obj=None, **kwargs):
        if not obj:
            return []
        self.parent_obj = obj

        # Allows us to do stuff with request before we're put inside the
        # AdminInlineFormSet helper class
        self.context = self.get_context(request, obj)

        return super(ChangeListInline, self).get_fieldsets(
            request, obj, **kwargs)

    def get_extra(self, request, obj=None, **kwargs):
        # There's no "add another" in this inline.
        return 0

    def get_add_url(self, request, obj, **kwargs):
        urlname = 'admin:{0.app_label}_{0.model_name}_add'
        url = reverse(urlname.format(self.model._meta))
        fk = self.get_fk_field(request, obj, **kwargs)
        if isinstance(fk, GenericFK):
            # generic fk
            ct_field, fk_field = fk
            parent_type = ContentType.objects.get_for_model(self.parent_obj)
            params = {
                ct_field.name: parent_type.pk,
                fk_field.name: self.parent_obj.pk
            }
        else:
            params = {
                fk.name: getattr(obj, fk.rel.field_name)
            }
        params.update(kwargs)
        return '?'.join((url, urllib.urlencode(params)))

    def get_queryset(self, request):
        qs = super(ChangeListInline, self).get_queryset(request)
        if not self.parent_obj:
            return qs.none()
        parent_type = ContentType.objects.get_for_model(self.parent_obj)
        fk = self.get_fk_field(request, None)
        if isinstance(fk, GenericFK):
            # generic fk
            ct_field, fk_field = fk
            filter = {
                ct_field.name: parent_type,
                fk_field.name: self.parent_obj.pk
            }
            return qs.filter(**filter)
        else:
            # regular fk
            return qs.filter(**{fk.name: self.parent_obj})

    def get_context(self, request, obj=None, extra_context=None):
        # hijack the context from the changelist_view template response
        response = self._modeladmin.changelist_view(request, extra_context)
        context = response.context_data
        context.update({
            'classes': ' '.join(self.classes),
            'add_url': self.get_add_url(request, obj)
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
