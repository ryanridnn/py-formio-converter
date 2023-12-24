import uuid
import xml.etree.ElementTree as ET
from utils import get_default_schema, write_json, get_key_and_content

# here are the important part

# enter the filepath to the xmljj
filename = "PHQ-9 (Extended Version).xml"

# enter the output path for the schema
schema_output = "../bitparlor/schema.json"

# enter the ouput path for the options, options file is for storing language localization mainly
options_output = "../bitparlor/options.json"


class FormioConverter:
    schema = {"components": []}
    schema_output = ""
    language_key_n_content = {}
    i18n = {}

    def __init__(self, filename, schema_output, options_output):
        self.filename = filename
        self.parsed = ET.parse(filename)
        self.root = self.parsed.getroot()

        self.schema_output = schema_output
        self.options_output = options_output
        self.process_root(self.root)

    def export(self):
        write_json(self.schema_output, self.schema)
        write_json(self.options_output, {"i18n": self.i18n})

    def process_root(self, root):
        self.get_header(root)

        fields = self.process_children(root)

        for field in fields:
            self.schema["components"].append(field)

        self.export()

    def process_children(self, parent, parents=[]):
        children = list(parent)
        fields = []

        if len(children) > 0:
            for child in parent:
                copied_parents = parents.copy()
                child_field = self.process_child(child, copied_parents)

                if child_field != None:
                    if child_field.get("__CANCEL_NESTING__") == True:
                        for inner_child in child_field["components"]:
                            fields.append(inner_child)
                    else:
                        fields.append(child_field)

        return fields

    def process_child(self, child, parents):
        field = {}
        new_parents = parents + [child.tag]

        if child.tag == "tagLine":
            field = self.get_content_schema(
                {"html": f"<p>{child.text}</p>", "key": "tagline"}
            )
        elif child.tag == "desc":
            field = self.get_content_schema(
                {
                    "html": f'<p style="font-size: 14px; color: #555;">{child.text}</p>',
                    "hidden": True,
                    "key": "desc",
                }
            )
        elif child.tag == "keywords":
            field = self.get_content_schema(
                {
                    "html": f'<p style="font-size: 14px; color: #555;">{child.text}</p>',
                    "hidden": True,
                    "key": "keywords",
                }
            )
        elif child.tag == "tags":
            field = self.process_tags(child)
        elif child.tag == "mainSection":
            field = {
                "__CANCEL_NESTING__": True,
                "components": self.process_children(child, new_parents),
            }
        elif child.tag == "section":
            field = {
                "__CANCEL_NESTING__": True,
                "components": self.process_children(child, new_parents),
            }
        elif child.tag == "items":
            field = self.process_items(child, new_parents)
        elif child.tag == "c":
            res = self.get_key_and_content(child.text)

            field = self.get_content_schema(
                {
                    "html": f'<p class="fs-6 lead">{res[1] if res else child.text}</p>',
                    "key": res[0] if res else "c1",
                }
            )
        elif child.tag == "item":
            field = self.process_item(child)
        elif child.tag == "refs":
            field = self.process_refs(child)
        elif child.tag == "stringTranslations":
            field = self.process_localization(child)
        else:
            return None

        return field

    def get_key_and_content(self, text):
        key_n_content = get_key_and_content(text)

        if key_n_content:
            self.language_key_n_content[key_n_content[0]] = key_n_content[1]

        return key_n_content

    def get_mapped_schema(self, field_type, new_schema):
        schema = get_default_schema(field_type)

        schema.update(new_schema)

        return schema

    def get_content_schema(self, new_schema):
        return self.get_mapped_schema("content", new_schema)

    def get_select_schema(self, new_schema):
        return self.get_mapped_schema("select", new_schema)

    def get_radio_schema(self, new_schema):
        return self.get_mapped_schema("radio", new_schema)

    def get_header(self, header):
        schema = get_default_schema("content")

        schema["html"] = f"<h2>{header.attrib['title']}</h2>"

        self.schema["components"].append(schema)

    def process_items(self, xml_element, parents):
        if xml_element.attrib.get("type"):
            return None
        else:
            return {
                "__CANCEL_NESTING__": True,
                "components": self.process_children(xml_element, parents),
            }

    def process_tags(self, element):
        tags = []

        for tag in element:
            if tag.text:
                tags.append(tag.text)

        if len(tags) == 0:
            return self.get_content_schema({"hidden": True, "html": "", "key": "tags"})
        else:
            html = f'<div class="d-flex gap-2 mb-4">'

            for tag in tags:
                html = html + f'<span class="badge text-bg-primary">{tag}</span>'

            html = html + f"</div>"

            return self.get_content_schema({"html": html, "key": "tags"})

    def process_item(self, xml_element):
        if xml_element.attrib.get("type") == "MENU":
            return self.process_item__menu(xml_element)
        elif xml_element.attrib.get("type") == "PROPOSITION":
            return self.process_item__proposition(xml_element)

        return None

    def process_item__menu(self, xml_element):
        schema = self.get_select_schema({})
        label = xml_element.find("c")
        desc = xml_element.find("cNote")
        validator = xml_element.find("validator")
        choices = xml_element.find("choices")

        if label is not None and choices is not None:
            key_n_content = self.get_key_and_content(label.text)

            options = self.get_menu_options(choices)

            schema = {
                "label": key_n_content[1] if key_n_content else label.text,
                "key": key_n_content[0] if key_n_content else str(uuid.uuid4),
                "data": {"values": options},
                "description": desc.text,
            }

            if validator.attrib.get("type") == "MANDATORY":
                schema["validate"] = {"required": True}

            schema = self.get_select_schema(schema)

            self.get_menu_options(choices)

            return schema
        else:
            return None

    def process_item__proposition(self, xml_element):
        label = xml_element.find("c")
        desc = xml_element.find("cNote")
        validator = xml_element.find("validator")

        posNote = xml_element.find("posNote")
        negNote = xml_element.find("negNote")

        if label is not None and posNote is not None and negNote is not None:
            key_n_content = self.get_key_and_content(label.text)

            values = [
                {"label": posNote.text, "value": "posNote"},
                {"label": negNote.text, "value": "negNote"},
            ]

            schema = {
                "label": key_n_content[1] if key_n_content else label.text,
                "values": values,
                "description": desc.text,
            }

            if validator.attrib.get("type") == "MANDATORY":
                schema["validate"] = {"required": True}

            schema = self.get_radio_schema(schema)

            return schema
        else:
            return None

    def get_menu_options(self, xml_element):
        choices = xml_element.findall("choice")
        options = []

        for choice in choices:
            display = choice.find("display")

            value = choice.attrib.get("val")
            if display is not None:
                key_n_content = self.get_key_and_content(display.text)

                options.append(
                    {
                        "label": key_n_content[1] if key_n_content else display.text,
                        "value": value,
                    }
                )

        return options

    def process_refs(self, xml_element):
        refs = xml_element.findall("ref")

        text = '<div class="mt-3"><div>Refs</div>'

        if len(refs) == 0:
            return None
        else:
            for ref in refs:
                url = ref.attrib.get("url")
                content = ref.attrib.get("text")
                text = (
                    text
                    + f'<div class="mt-2"><a href="{url}" target="_blank">{content}</a></div>'
                )

        text = text + "</div>"

        schema = self.get_content_schema({"html": text, "key": "refs"})

        return schema

    def process_localization(self, xml_element):
        blocks = list(xml_element)

        for block in blocks:
            language = block.attrib.get("locale")
            ref = block.attrib.get("ref")
            text = block.text

            if language is not None and ref is not None and text is not None:
                en = self.language_key_n_content.get(ref)

                if en is None:
                    break

                language = language.lower()

                is_exist = self.i18n.get(language)

                if is_exist:
                    self.i18n[language][en] = text
                else:
                    self.i18n[language] = {en: text}


formio_converter = FormioConverter(filename, schema_output, options_output)
