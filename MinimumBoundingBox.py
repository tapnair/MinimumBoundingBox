import adsk.core
import adsk.fusion
import traceback

app = adsk.core.Application.get()
ui = app.userInterface

# If set True a custom Graphics Body will be displayed
CREATE_CUSTOM_GRAPHICS = True

# If set True a solid Body will be created
CREATE_BREP_BODY = False


def run(context):
    try:
        selection = ui.selectEntity('Pick a body', 'Bodies')
        body = adsk.fusion.BRepBody.cast(selection.entity)
        if body is None:
            ui.messageBox(f'Did not select valid body')
            return

        result_box = get_minimum_bounding_box(body)

        msg = make_value_message_row('Length', result_box)
        msg += make_value_message_row('Width', result_box)
        msg += make_value_message_row('Height', result_box)
        msg += make_vector_message_row('X Axis', result_box)
        msg += make_vector_message_row('Y Axis', result_box)
        msg += make_vector_message_row('Z Axis', result_box)
        ui.messageBox(msg)

        if CREATE_CUSTOM_GRAPHICS:
            result_box['graphics_group'].deleteMe()

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def get_minimum_bounding_box(body: adsk.fusion.BRepBody):
    temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()
    t_body = temp_brep_mgr.copy(body)

    physical_props = body.getPhysicalProperties(adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy)
    (returnValue, x_axis, y_axis, z_axis) = physical_props.getPrincipalAxes()
    com = physical_props.centerOfMass

    design = get_design()
    orientation_reference_component = design.rootComponent
    # orientation_reference_component = body.parentComponent

    matrix = adsk.core.Matrix3D.create()
    matrix.setToAlignCoordinateSystems(
        com, x_axis, y_axis, z_axis, com,
        orientation_reference_component.xConstructionAxis.geometry.direction,
        orientation_reference_component.yConstructionAxis.geometry.direction,
        orientation_reference_component.zConstructionAxis.geometry.direction
    )

    temp_brep_mgr.transform(t_body, matrix)

    oriented_bounding_box = oriented_b_box_from_b_box(t_body.boundingBox)

    graphics_group = None
    if CREATE_CUSTOM_GRAPHICS or CREATE_BREP_BODY:
        graphics_group = create_oriented_box(
            oriented_bounding_box,
            com,
            orientation_reference_component,
            x_axis, y_axis, z_axis
        )

    return {
        'Length': oriented_bounding_box.length,
        'Width': oriented_bounding_box.width,
        'Height': oriented_bounding_box.height,
        'X Axis': x_axis,
        'Y Axis': y_axis,
        'Z Axis': z_axis,
        'graphics_group': graphics_group,
    }


def oriented_b_box_from_b_box(b_box: adsk.core.BoundingBox3D) -> adsk.core.OrientedBoundingBox3D:
    design = get_design()
    root_comp = design.rootComponent

    o_box = adsk.core.OrientedBoundingBox3D.create(
        mid_point(b_box.minPoint, b_box.maxPoint),
        root_comp.yZConstructionPlane.geometry.normal.copy(),
        root_comp.xZConstructionPlane.geometry.normal.copy(),
        b_box.maxPoint.x - b_box.minPoint.x,
        b_box.maxPoint.y - b_box.minPoint.y,
        b_box.maxPoint.z - b_box.minPoint.z
    )
    return o_box


def mid_point(p1: adsk.core.Point3D, p2: adsk.core.Point3D) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(
        middle(p1.x, p2.x),
        middle(p1.y, p2.y),
        middle(p1.z, p2.z)
    )


def middle(min_p_value: float, max_p_value: float) -> float:
    return min_p_value + ((max_p_value - min_p_value) / 2)


def get_design() -> adsk.fusion.Design:
    _design = app.activeDocument.products.itemByProductType('DesignProductType')
    design = adsk.fusion.Design.cast(_design)
    return design


def create_oriented_box(oriented_bounding_box, com, orientation_reference_component: adsk.fusion.Component, x_axis,
                        y_axis, z_axis):
    temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()
    box_temp_body = temp_brep_mgr.createBox(oriented_bounding_box)

    matrix = adsk.core.Matrix3D.create()
    matrix.setToAlignCoordinateSystems(
        com,
        orientation_reference_component.xConstructionAxis.geometry.direction,
        orientation_reference_component.yConstructionAxis.geometry.direction,
        orientation_reference_component.zConstructionAxis.geometry.direction,
        com,
        x_axis, y_axis, z_axis
    )

    temp_brep_mgr.transform(box_temp_body, matrix)
    graphics_group = None

    if CREATE_CUSTOM_GRAPHICS:
        graphics_group = orientation_reference_component.customGraphicsGroups.add()
        graphics_box = graphics_group.addBRepBody(box_temp_body)

        this_color = adsk.core.Color.create(240, 150, 50, 255)
        this_color_effect = adsk.fusion.CustomGraphicsSolidColorEffect.create(this_color)
        graphics_box.color = this_color_effect
        graphics_box.setOpacity(.4, True)

    if CREATE_BREP_BODY:
        design = get_design()
        root_component = design.rootComponent
        if design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
            base_feature = root_component.features.baseFeatures.add()
            base_feature.startEdit()
            root_component.bRepBodies.add(box_temp_body, base_feature)
            base_feature.finishEdit()
        else:
            root_component.bRepBodies.add(box_temp_body)

    return graphics_group


def make_value_message_row(name, result_box):
    value = result_box[name]
    design = get_design()
    units_manager = design.fusionUnitsManager
    display_value = units_manager.formatInternalValue(value)
    # msg = f'{name}: {display_value:.2f}\n'
    msg = f'{name}: {display_value}\n'
    return msg


def make_vector_message_row(name, result_box):
    vector: adsk.core.Vector3D = result_box[name].copy()
    vector.normalize()
    # msg = f'{name}: {display_value:.2f}\n'
    msg = f'{name} - Vector: {vector.x:.4f}, {vector.y:.4f}, {vector.z:.4f}\n'
    return msg
