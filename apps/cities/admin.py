from django.contrib import admin
from import_export import resources, fields, widgets
from .models import Locality, Region, District
from pytils.translit import slugify
from import_export.admin import ImportExportModelAdmin


class RegionWidget(widgets.ForeignKeyWidget):
    def __init__(self):
        super().__init__(Region, field="name")


class DistrictWidget(widgets.ForeignKeyWidget):
    def __init__(self):
        super().__init__(District, field="name")

class LocalityTypeWidget(widgets.Widget):
    mapping = {
        "Город": "city",
        "Деревня": "village",
        "Посёлок": "town",
        "Село": "selo",
        "Посёлок городского типа": "urban-type",
        "Рабочий посёлок": "work-town",
    }

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return ""
        value = value.strip()
        if value not in self.mapping:
            raise ValueError(f"Неверный тип населённого пункта: {value}")
        return self.mapping[value]

    def render(self, value, obj=None, *args, **kwargs):
        reverse_mapping = {v: k for k, v in self.mapping.items()}
        return reverse_mapping.get(value, "")


class LocalityResource(resources.ModelResource):
    name = fields.Field(column_name="Название", attribute="name")
    name_prepositional = fields.Field(
        column_name="Название (предложный падеж)", attribute="name_prepositional"
    )
    slug = fields.Field(column_name="URL-адрес", attribute="slug")
    locality_type = fields.Field(
        column_name="Тип", attribute="locality_type", widget=LocalityTypeWidget()
    )
    region = fields.Field(
        column_name="Регион",
        attribute="region",
        widget=RegionWidget(),
    )
    district = fields.Field(
        column_name="Район",
        attribute="district",
        widget=DistrictWidget(),
    )
    is_active = fields.Field(
        column_name="Активен", attribute="is_active", widget=widgets.BooleanWidget()
    )

    def before_import_row(self, row, **kwargs):
        region_name = row.get("Регион")
        district_name = row.get("Район")
        name = row.get("Название")

        region = None
        if region_name:
            region, _ = Region.objects.get_or_create(name=region_name)
            row["Регион"] = region.name

        if district_name and region:
            district, _ = District.objects.get_or_create(name=district_name, region=region)
            row["Район"] = district.name

        slug = row.get("URL-адрес")
        if not slug and region and name:
            try:
                locality = Locality.objects.get(name=name, region=region)
                row["URL-адрес"] = locality.slug
            except Locality.DoesNotExist:
                pass

    def before_save_instance(self, instance, row, **kwargs):
        if not instance.slug:
            instance.slug = slugify(instance.name)
        return super().before_save_instance(instance, row, **kwargs)

    class Meta:
        model = Locality
        import_id_fields = ("slug",)
        fields = (
            "name",
            "name_prepositional",
            "slug",
            "locality_type",
            "region",
            "district",
            "is_active",
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    list_filter = ("region",)
    search_fields = ("name",)


@admin.register(Locality)
class LocalityAdmin(ImportExportModelAdmin):
    resource_class = LocalityResource
    list_display = ("name", "locality_type", "district", "is_active")
    list_filter = ("locality_type", "is_active", "district__region")
    search_fields = ("name", "name_prepositional")
    prepopulated_fields = {"slug": ("name",)}
