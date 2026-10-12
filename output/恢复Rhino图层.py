# -*- coding: utf-8 -*-
"""Rhino 7/8: import the 3DS into an empty meters document, then run this script.
Uses object names and layer_map.json; does not rescale geometry or alter document units.
"""
import os
import json
import rhinoscriptsyntax as rs
import scriptcontext as sc
from System.Drawing import Color

def restore_layers():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layer_map.json')
    except NameError:
        path = None
    if not path or not os.path.isfile(path):
        path = rs.OpenFileName('选择随模型提供的 layer_map.json', 'JSON (*.json)|*.json||')
    if not path:
        return
    with open(path, 'rb') as stream:
        table = json.loads(stream.read().decode('utf-8'))
    count = 0
    undo = sc.doc.BeginUndoRecord('恢复创新港建筑图层')
    rs.EnableRedraw(False)
    try:
        for obj in list(sc.doc.Objects):
            name = obj.Attributes.Name
            entry = table.get(name)
            if entry is None:
                continue
            layer = entry['layer']
            if not rs.IsLayer(layer):
                rgb = entry['color']
                rs.AddLayer(layer, Color.FromArgb(*rgb))
            rs.ObjectLayer(obj.Id, layer)
            rs.SetUserText(obj.Id, '模型来源', '创新港公开资料体块模型；1单位=1米')
            count += 1
    finally:
        rs.EnableRedraw(True)
        sc.doc.EndUndoRecord(undo)
    print('已恢复 {0} 个对象的图层。建筑逐栋分层，环境共用一层。'.format(count))
    if count == 0:
        rs.MessageBox('未找到对应名称的对象。请先导入随附3DS文件，或直接打开分层3DM。', 0, '创新港模型')
    sc.doc.Views.Redraw()

if __name__ == '__main__':
    restore_layers()
