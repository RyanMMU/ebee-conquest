api = None
toolbox_open = False
previous_owners = {}


def onload(script_api):
    global api
    api = script_api
    register_toggle()
    api.log("developer toolbox loaded")


def onunload(script_api):
    script_api.unregister_ui()


def register_toggle():
    api.register_ui_button(
        "toolbox_toggle",
        x=-44,
        y=92,
        width=36,
        height=34,
        label="<",
        anchor="bottomright",
        on_click=toggle_toolbox,
    )


def toggle_toolbox(payload):
    global toolbox_open
    toolbox_open = not toolbox_open
    if toolbox_open:
        open_toolbox()
    else:
        close_toolbox()
    register_toggle()


def open_toolbox():
    api.register_ui_panel(
        "toolbox_panel",
        x=-320,
        y=134,
        width=300,
        height=292,
        title="TEST TOOLBOX",
        anchor="topright",
    )

    add_button("gold_plus", 176, "+1000 gold", add_gold)
    add_button("gold_minus", 214, "-1000 gold", remove_gold)
    add_button("army_plus", 252, "+1000 army", add_army)
    add_button("army_minus", 290, "-1000 army", remove_army)
    add_button("annex", 328, "annex province", annex_province)
    add_button("cede", 366, "cede province", cede_province)


def close_toolbox():
    for ui_id in (
        "toolbox_panel",
        "gold_plus",
        "gold_minus",
        "army_plus",
        "army_minus",
        "annex",
        "cede",
    ):
        api.unregister_ui(ui_id)


def add_button(ui_id, y, label, callback):
    api.register_ui_button(
        ui_id,
        x=-300,
        y=y,
        width=260,
        height=30,
        label=label,
        anchor="topright",
        on_click=callback,
        parent="toolbox_panel",
    )


def selected_country():
    country = api.get_selected_country()
    if not country:
        api.show_script_message("no selected or player country")
        return None
    return country


def selected_province_id():
    province_id = api.get_selected_province_id()
    if not province_id:
        api.show_script_message("select a province first")
        return None
    return province_id


def add_gold(payload):
    country = selected_country()
    if not country:
        return

    total = api.add_gold(country, 1000)
    api.show_script_message(f"{country}: gold is now {total}")


def remove_gold(payload):
    country = selected_country()
    if not country:
        return

    total = api.add_gold(country, -1000)
    api.show_script_message(f"{country}: gold is now {total}")


def add_army(payload):
    province_id = selected_province_id()
    if not province_id:
        return

    total = api.add_army(province_id, 1000)
    if total is None:
        api.show_script_message("selected province was not found")
        return
    api.show_script_message(f"{province_id}: troops are now {total}")


def remove_army(payload):
    province_id = selected_province_id()
    if not province_id:
        return

    total = api.add_army(province_id, -1000)
    if total is None:
        api.show_script_message("selected province was not found")
        return
    api.show_script_message(f"{province_id}: troops are now {total}")


def annex_province(payload):
    country = selected_country()
    province_id = selected_province_id()
    if not country or not province_id:
        return

    province = api.get_province_data(province_id)
    old_owner = province.get("ownerCountry") or province.get("controllerCountry")
    if old_owner and province_id not in previous_owners:
        previous_owners[province_id] = old_owner

    owner_result = api.set_province_owner(province_id, country)
    controller_result = api.set_province_controller(province_id, country)
    if owner_result is None or controller_result is None:
        api.show_script_message("selected province was not found")
        return

    api.show_script_message(f"{province_id} annexed by {country}")


def cede_province(payload):
    province_id = selected_province_id()
    if not province_id:
        return

    province = api.get_province_data(province_id)
    current_owner = province.get("ownerCountry")
    current_controller = province.get("controllerCountry")
    target = previous_owners.get(province_id)

    if not target or target == current_owner:
        target = current_owner if current_controller != current_owner else None

    if not target:
        api.show_script_message("no previous owner to cede this province to")
        return

    api.set_province_owner(province_id, target)
    api.set_province_controller(province_id, target)
    previous_owners.pop(province_id, None)
    api.show_script_message(f"{province_id} ceded to {target}")
