"""Skin selector dialog: visual character grid with metadata, abilities, and instant switching."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango
from skins.manager import skin_manager


class SkinSelectorDialog(Gtk.Dialog):
    """Modern character selector dialog."""

    def __init__(self, engine, parent=None):
        super().__init__(
            title="Buddy — Select Character Skin",
            transient_for=parent,
            flags=0
        )
        self.engine = engine
        self.selected_skin_id = engine.character.skin_id
        self.set_default_size(680, 520)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Header bar
        header = Gtk.HeaderBar(title="Buddy Character Gallery", show_close_button=True)
        header.set_subtitle("Choose your desktop superhero or fantasy companion")
        self.set_titlebar(header)

        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(14)
        content.set_margin_bottom(14)
        content.set_margin_left(16)
        content.set_margin_right(16)

        # Scrollable container
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content.pack_start(scroller, True, True, 0)

        # Grid / FlowBox for skins
        self.flow = Gtk.FlowBox()
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_max_children_per_line(3)
        self.flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flow.set_homogeneous(True)
        self.flow.set_column_spacing(12)
        self.flow.set_row_spacing(12)
        scroller.add(self.flow)

        skins = skin_manager.get_available_skins()
        self.cards = {}
        for meta in skins:
            card = self._create_skin_card(meta)
            self.flow.add(card)
            self.cards[meta["id"]] = card

        # Connect selection
        self.flow.connect("child-activated", self._on_child_activated)

        # Action Buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        apply_btn = self.add_button("Apply Skin", Gtk.ResponseType.APPLY)
        apply_btn.get_style_context().add_class("suggested-action")

        self.show_all()

    def _create_skin_card(self, meta: dict) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_left(10)
        box.set_margin_right(10)

        # Skin name
        name_lbl = Gtk.Label()
        name_lbl.set_markup(f"<b><big>{meta.get('name', 'Unknown')}</big></b>")
        name_lbl.set_xalign(0.0)
        box.pack_start(name_lbl, False, False, 0)

        # Flight tag / Category
        tags = []
        if meta.get("canFly", False):
            tags.append("🕊️ Flight")
        category = meta.get("category", "hero")
        tags.append(f"⭐ {category.capitalize()}")
        tag_lbl = Gtk.Label(label=" • ".join(tags))
        tag_lbl.set_xalign(0.0)
        box.pack_start(tag_lbl, False, False, 0)

        # Description
        desc_lbl = Gtk.Label(label=meta.get("description", ""))
        desc_lbl.set_line_wrap(True)
        desc_lbl.set_max_width_chars(28)
        desc_lbl.set_xalign(0.0)
        box.pack_start(desc_lbl, True, True, 0)

        # Abilities list
        abilities = meta.get("abilities", [])
        if abilities:
            ab_text = "Abilities: " + ", ".join([a.replace("_", " ").title() for a in abilities[:3]])
            ab_lbl = Gtk.Label()
            ab_lbl.set_markup(f"<small><i>{ab_text}</i></small>")
            ab_lbl.set_xalign(0.0)
            box.pack_start(ab_lbl, False, False, 0)

        box.skin_id = meta["id"]
        return box

    def _on_child_activated(self, flowbox, child):
        box = child.get_child()
        self.selected_skin_id = getattr(box, "skin_id", "thor")


def show_skin_selector(engine):
    dialog = SkinSelectorDialog(engine)
    response = dialog.run()
    if response == Gtk.ResponseType.APPLY:
        engine.switch_skin(dialog.selected_skin_id)
    dialog.destroy()
