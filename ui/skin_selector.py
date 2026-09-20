"""Skin Gallery dialog: modern visual character browser with categories, search, personality metrics, and abilities."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango
from skins.manager import skin_manager


class SkinSelectorDialog(Gtk.Dialog):
    """Modern Buddy 2.0 visual skin gallery and character browser."""

    CATEGORIES = ["All", "Heroes", "Animals", "Fantasy", "Sci-Fi", "Cute"]

    def __init__(self, engine, parent=None):
        super().__init__(
            title="Buddy — Character Gallery",
            transient_for=parent,
            flags=0
        )
        self.engine = engine
        self.selected_skin_id = engine.character.skin_id
        self.active_category = "All"
        self.search_query = ""

        self.set_default_size(840, 580)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Header Bar
        header = Gtk.HeaderBar(title="Buddy Character Gallery", show_close_button=True)
        header.set_subtitle("Browse personalities, abilities, and desktop companions")
        self.set_titlebar(header)

        main_content = self.get_content_area()
        main_content.set_spacing(10)
        main_content.set_margin_top(12)
        main_content.set_margin_bottom(12)
        main_content.set_margin_left(14)
        main_content.set_margin_right(14)

        # Top Control Bar: Search and Categories
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_content.pack_start(top_bar, False, False, 0)

        # Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search companion or ability...")
        self.search_entry.set_width_chars(24)
        self.search_entry.connect("search-changed", self._on_search_changed)
        top_bar.pack_start(self.search_entry, False, False, 0)

        # Category Buttons
        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.cat_buttons = {}
        for cat in self.CATEGORIES:
            btn = Gtk.ToggleButton(label=cat)
            if cat == "All":
                btn.set_active(True)
            btn.connect("toggled", self._on_category_toggled, cat)
            cat_box.pack_start(btn, False, False, 0)
            self.cat_buttons[cat] = btn
        top_bar.pack_start(cat_box, True, True, 0)

        # Split Pane: Gallery Grid on left, Detailed Info Panel on right
        paned = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        main_content.pack_start(paned, True, True, 0)

        # Left: Scrollable Grid
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_width(480)
        paned.pack_start(scroller, True, True, 0)

        self.flow = Gtk.FlowBox()
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_max_children_per_line(2)
        self.flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flow.set_homogeneous(True)
        self.flow.set_column_spacing(10)
        self.flow.set_row_spacing(10)
        self.flow.set_filter_func(self._filter_skin_card)
        scroller.add(self.flow)

        # Populate Skin Cards
        self.cards = {}
        skins = skin_manager.get_available_skins()
        for meta in skins:
            card = self._create_skin_card(meta)
            self.flow.add(card)
            self.cards[meta["id"]] = card

        self.flow.set_activate_on_single_click(True)
        self.flow.connect("selected-children-changed", self._on_selected_children_changed)
        self.flow.connect("child-activated", self._on_child_activated)

        # Right: Detail Sidebar
        self.detail_panel = self._create_detail_panel()
        paned.pack_start(self.detail_panel, False, False, 0)

        # Bottom Action Bar
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.apply_btn = self.add_button(f"Use This Buddy", Gtk.ResponseType.APPLY)
        self.apply_btn.get_style_context().add_class("suggested-action")

        self.show_all()

        # Select currently active skin
        for child in self.flow.get_children():
            box = child.get_child()
            if getattr(box, "skin_id", "") == self.selected_skin_id:
                self.flow.select_child(child)
                self._update_detail_panel(skin_manager.get_metadata(self.selected_skin_id) or {})
                break

    def _create_skin_card(self, meta: dict) -> Gtk.Widget:
        """Card widget inside the FlowBox."""
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_left(10)
        box.set_margin_right(10)
        frame.add(box)

        # Name + Active Indicator
        is_active = (meta["id"] == self.selected_skin_id)
        active_badge = " ✓ Active" if is_active else ""
        name_lbl = Gtk.Label()
        name_lbl.set_markup(f"<b>{meta.get('name', 'Unknown')}</b> <small><span color='#2ecc71'>{active_badge}</span></small>")
        name_lbl.set_xalign(0.0)
        box.pack_start(name_lbl, False, False, 0)

        # Category and Tag
        cat = meta.get("category", "original").capitalize()
        fly_str = " • 🕊️ Fly" if meta.get("canFly", False) else ""
        cat_lbl = Gtk.Label(label=f"{cat}{fly_str}")
        cat_lbl.get_style_context().add_class("dim-label")
        cat_lbl.set_xalign(0.0)
        box.pack_start(cat_lbl, False, False, 0)

        # Short summary
        desc = meta.get("description", "")
        if len(desc) > 75:
            desc = desc[:72] + "..."
        desc_lbl = Gtk.Label(label=desc)
        desc_lbl.set_line_wrap(True)
        desc_lbl.set_max_width_chars(24)
        desc_lbl.set_xalign(0.0)
        box.pack_start(desc_lbl, True, True, 0)

        # Ability tags
        abilities = meta.get("abilities", [])
        if abilities:
            ab_str = "⚡ " + ", ".join([a.replace("_", " ").title() for a in abilities[:2]])
            ab_lbl = Gtk.Label()
            ab_lbl.set_markup(f"<small><i>{ab_str}</i></small>")
            ab_lbl.set_xalign(0.0)
            box.pack_start(ab_lbl, False, False, 0)

        box.skin_id = meta["id"]
        box.meta = meta
        return frame

    def _create_detail_panel(self) -> Gtk.Widget:
        """Right sidebar displaying in-depth character personality and abilities."""
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        frame.set_min_content_width(280)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(14)
        vbox.set_margin_left(14)
        vbox.set_margin_right(14)
        frame.add(vbox)

        # Title
        self.detail_title = Gtk.Label()
        self.detail_title.set_markup("<b><big>Character Details</big></b>")
        self.detail_title.set_xalign(0.0)
        vbox.pack_start(self.detail_title, False, False, 0)

        self.detail_subtitle = Gtk.Label()
        self.detail_subtitle.set_xalign(0.0)
        vbox.pack_start(self.detail_subtitle, False, False, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Full Description
        self.detail_desc = Gtk.Label()
        self.detail_desc.set_line_wrap(True)
        self.detail_desc.set_xalign(0.0)
        vbox.pack_start(self.detail_desc, False, False, 4)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Personality Meters Section
        p_hdr = Gtk.Label()
        p_hdr.set_markup("<b>Personality Profile</b>")
        p_hdr.set_xalign(0.0)
        vbox.pack_start(p_hdr, False, False, 0)

        self.bar_energy = self._create_metric_row(vbox, "⚡ Energy:")
        self.bar_curiosity = self._create_metric_row(vbox, "🔍 Curiosity:")
        self.bar_playfulness = self._create_metric_row(vbox, "🎈 Playfulness:")

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Full Abilities List
        ab_hdr = Gtk.Label()
        ab_hdr.set_markup("<b>Special Abilities</b>")
        ab_hdr.set_xalign(0.0)
        vbox.pack_start(ab_hdr, False, False, 0)

        self.detail_abilities = Gtk.Label()
        self.detail_abilities.set_line_wrap(True)
        self.detail_abilities.set_xalign(0.0)
        vbox.pack_start(self.detail_abilities, True, True, 0)

        return frame

    def _create_metric_row(self, container: Gtk.Box, label_text: str) -> Gtk.ProgressBar:
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=label_text)
        lbl.set_width_chars(12)
        lbl.set_xalign(0.0)
        bar = Gtk.ProgressBar()
        bar.set_fraction(0.5)
        bar.set_show_text(True)
        hbox.pack_start(lbl, False, False, 0)
        hbox.pack_start(bar, True, True, 0)
        container.pack_start(hbox, False, False, 2)
        return bar

    def _update_detail_panel(self, meta: dict) -> None:
        """Update detail sidebar with selected skin's attributes."""
        if not meta:
            return

        name = meta.get("name", "Unknown")
        cat = meta.get("category", "General").capitalize()
        fly_str = " • 🕊️ Can Fly" if meta.get("canFly", False) else " • 🐾 Ground"
        self.detail_title.set_markup(f"<b><big>{name}</big></b>")
        self.detail_subtitle.set_markup(f"<small>{cat}{fly_str}</small>")
        self.detail_desc.set_text(meta.get("description", "No description available."))

        # Personality metrics
        personality = meta.get("personality", {})
        energy = float(personality.get("energy", 0.7))
        curiosity = float(personality.get("curiosity", 0.6))
        playfulness = float(personality.get("playfulness", 0.6))

        self.bar_energy.set_fraction(energy)
        self.bar_energy.set_text(f"{int(energy * 100)}%")
        self.bar_curiosity.set_fraction(curiosity)
        self.bar_curiosity.set_text(f"{int(curiosity * 100)}%")
        self.bar_playfulness.set_fraction(playfulness)
        self.bar_playfulness.set_text(f"{int(playfulness * 100)}%")

        # Abilities list
        abs_list = meta.get("abilities", [])
        if abs_list:
            lines = [f"• <b>{a.replace('_', ' ').title()}</b>" for a in abs_list]
            self.detail_abilities.set_markup("\n".join(lines))
        else:
            self.detail_abilities.set_text("Default desktop movement and companion interactions.")

    def _filter_skin_card(self, child: Gtk.FlowBoxChild) -> bool:
        """Filter FlowBox items by active category and search query."""
        frame = child.get_child()
        box = frame.get_child()
        meta = getattr(box, "meta", {})
        if not meta:
            return True

        # 1. Category check
        if self.active_category != "All":
            meta_cat = str(meta.get("category", "")).lower()
            target_cat = self.active_category.lower()
            if target_cat == "heroes":
                if "hero" not in meta_cat:
                    return False
            elif target_cat not in meta_cat:
                return False

        # 2. Search query check
        if self.search_query:
            q = self.search_query.lower()
            name = str(meta.get("name", "")).lower()
            desc = str(meta.get("description", "")).lower()
            abilities = " ".join(meta.get("abilities", [])).lower()
            if q not in name and q not in desc and q not in abilities:
                return False

        return True

    def _on_category_toggled(self, button: Gtk.ToggleButton, category: str) -> None:
        if button.get_active():
            self.active_category = category
            # Deselect other category buttons
            for cat, btn in self.cat_buttons.items():
                if cat != category and btn.get_active():
                    btn.set_active(False)
            self.flow.invalidate_filter()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.search_query = entry.get_text().strip()
        self.flow.invalidate_filter()

    def _on_selected_children_changed(self, flowbox: Gtk.FlowBox) -> None:
        selected = flowbox.get_selected_children()
        if selected:
            frame = selected[0].get_child()
            box = frame.get_child()
            sid = getattr(box, "skin_id", None)
            meta = getattr(box, "meta", None)
            if sid and meta:
                self.selected_skin_id = sid
                self.apply_btn.set_label(f"Use {meta.get('name', sid)}")
                self._update_detail_panel(meta)

    def _on_child_activated(self, flowbox: Gtk.FlowBox, child: Gtk.FlowBoxChild) -> None:
        frame = child.get_child()
        box = frame.get_child()
        sid = getattr(box, "skin_id", None)
        if sid:
            self.selected_skin_id = sid
        self.response(Gtk.ResponseType.APPLY)


def show_skin_selector(engine, parent=None):
    """Open the modern Buddy 2.0 Skin Gallery dialog."""
    dialog = SkinSelectorDialog(engine, parent=parent)
    response = dialog.run()
    if response in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK, Gtk.ResponseType.ACCEPT):
        engine.switch_skin(dialog.selected_skin_id)
    dialog.destroy()
