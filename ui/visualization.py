"""
Module de Visualisation Quantique en Temps Réel
Interface de monitoring et visualisation des corrélations Bell
"""

import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False

import sys
sys.path.append('..')

from ..core.quantum_verification import AdvancedBellVerification, QuantumCoherenceMonitor


if BLENDER_AVAILABLE:
    
    class POLYSPINOR_OT_ShowBellCorrelations(bpy.types.Operator):
        """Affiche les corrélations de Bell"""
        bl_idname = "polyspinor.show_bell_correlations"
        bl_label = "Afficher Corrélations Bell"
        bl_description = "Visualise les corrélations quantiques de Bell"
        
        def execute(self, context):
            try:
                verifier = AdvancedBellVerification()
                state = verifier.prepare_7d_entangled_state()
                correlations = verifier.build_correlation_tensor(4, 4)
                
                self._create_correlation_visualization(correlations)
                
                if hasattr(context.scene, 'polyspinor_correlations'):
                    context.scene.polyspinor_correlations = tuple(
                        correlations.flatten()[:7].tolist()
                    )
                
                self.report({'INFO'}, "Corrélations Bell visualisées")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur: {str(e)}")
                return {'CANCELLED'}
        
        def _create_correlation_visualization(self, correlations: np.ndarray):
            """Crée une visualisation des corrélations"""
            bpy.ops.object.select_all(action='DESELECT')
            
            for i in range(correlations.shape[0]):
                for j in range(correlations.shape[1]):
                    val = correlations[i, j]
                    
                    bpy.ops.mesh.primitive_cube_add(
                        size=0.3,
                        location=(i * 0.5, j * 0.5, val * 2)
                    )
                    obj = bpy.context.active_object
                    obj.name = f"Correlation_{i}_{j}"
                    
                    mat = bpy.data.materials.new(name=f"CorrMat_{i}_{j}")
                    if val > 0:
                        mat.diffuse_color = (0.2, 0.8, 0.2, 1.0)
                    else:
                        mat.diffuse_color = (0.8, 0.2, 0.2, 1.0)
                    
                    if obj.data.materials:
                        obj.data.materials[0] = mat
                    else:
                        obj.data.materials.append(mat)
    
    
    class POLYSPINOR_OT_ShowEntanglement(bpy.types.Operator):
        """Affiche l'intrication quantique"""
        bl_idname = "polyspinor.show_entanglement"
        bl_label = "Afficher Intrication"
        bl_description = "Visualise l'intrication quantique entre les clusters"
        
        def execute(self, context):
            try:
                verifier = AdvancedBellVerification()
                state = verifier.prepare_7d_entangled_state()
                
                self._create_entanglement_visualization(state)
                
                self.report({'INFO'}, "Intrication visualisée")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur: {str(e)}")
                return {'CANCELLED'}
        
        def _create_entanglement_visualization(self, state: np.ndarray):
            """Crée une visualisation de l'intrication"""
            n = len(state)
            
            positions = []
            for i in range(n):
                angle = 2 * np.pi * i / n
                x = np.cos(angle) * 5
                y = np.sin(angle) * 5
                z = np.abs(state[i]) * 3
                positions.append((x, y, z))
            
            for i, pos in enumerate(positions):
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=0.2,
                    location=pos
                )
                obj = bpy.context.active_object
                obj.name = f"Qudit_{i}"
                
                mat = bpy.data.materials.new(name=f"QuditMat_{i}")
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                emission = nodes.get('Emission')
                if not emission:
                    emission = nodes.new(type='ShaderNodeEmission')
                
                phase = np.angle(state[i])
                r = (np.sin(phase) + 1) / 2
                g = (np.cos(phase) + 1) / 2
                b = 0.5
                emission.inputs['Color'].default_value = (r, g, b, 1.0)
                emission.inputs['Strength'].default_value = 2.0
                
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
            
            self._create_entanglement_lines(positions, state)
        
        def _create_entanglement_lines(self, positions: List, state: np.ndarray):
            """Crée des lignes représentant l'intrication"""
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    correlation = np.abs(state[i] * np.conj(state[j]))
                    
                    if correlation > 0.01:
                        curve = bpy.data.curves.new(
                            name=f"Entangle_{i}_{j}",
                            type='CURVE'
                        )
                        curve.dimensions = '3D'
                        
                        spline = curve.splines.new(type='BEZIER')
                        spline.bezier_points.add(1)
                        
                        spline.bezier_points[0].co = positions[i]
                        spline.bezier_points[1].co = positions[j]
                        
                        obj = bpy.data.objects.new(f"Entangle_{i}_{j}", curve)
                        bpy.context.collection.objects.link(obj)
                        
                        curve.bevel_depth = 0.02 * correlation * 10
    
    
    class POLYSPINOR_OT_RefreshMonitoring(bpy.types.Operator):
        """Rafraîchit le monitoring quantique"""
        bl_idname = "polyspinor.refresh_monitoring"
        bl_label = "Rafraîchir Monitoring"
        bl_description = "Met à jour les valeurs de monitoring en temps réel"
        
        def execute(self, context):
            try:
                verifier = AdvancedBellVerification()
                monitor = QuantumCoherenceMonitor()
                
                state = verifier.prepare_7d_entangled_state()
                
                coherence = monitor.measure_coherence(state)
                
                correlations = verifier.build_correlation_tensor(2, 2)
                chsh = abs(
                    correlations[0,0] + correlations[0,1] + 
                    correlations[1,0] - correlations[1,1]
                )
                
                if hasattr(context.scene, 'polyspinor_entropy'):
                    context.scene.polyspinor_entropy = coherence
                
                if hasattr(context.scene, 'polyspinor_monitoring_status'):
                    context.scene.polyspinor_monitoring_status = \
                        f"Cohérence: {coherence:.3f} | CHSH: {chsh:.3f}"
                
                self.report({'INFO'}, f"Monitoring mis à jour: cohérence={coherence:.3f}")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur monitoring: {str(e)}")
                return {'CANCELLED'}
    
    
    class POLYSPINOR_OT_ExportQuantumData(bpy.types.Operator):
        """Exporte les données quantiques"""
        bl_idname = "polyspinor.export_quantum_data"
        bl_label = "Exporter Données Quantiques"
        bl_description = "Exporte les données quantiques en format JSON"
        
        filepath: bpy.props.StringProperty(subtype='FILE_PATH')
        
        def execute(self, context):
            import json
            
            try:
                data = {
                    'timestamp': datetime.now().isoformat(),
                    'key_7d': list(context.scene.polyspinor_7d_key) \
                              if hasattr(context.scene, 'polyspinor_7d_key') else [],
                    'entropy': context.scene.polyspinor_entropy \
                              if hasattr(context.scene, 'polyspinor_entropy') else 0,
                    'correlations': list(context.scene.polyspinor_correlations) \
                                   if hasattr(context.scene, 'polyspinor_correlations') else [],
                    'security_enabled': context.scene.polyspinor_security_enabled \
                                       if hasattr(context.scene, 'polyspinor_security_enabled') else True
                }
                
                with open(self.filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.report({'INFO'}, f"Données exportées: {self.filepath}")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur export: {str(e)}")
                return {'CANCELLED'}
        
        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
    
    
    class POLYSPINOR_PT_QuantumVisualization(bpy.types.Panel):
        """Panneau de visualisation quantique avancée"""
        bl_label = "Visualisation Quantique 7D"
        bl_idname = "POLYSPINOR_PT_quantum_visualization"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "PolySpinor"
        bl_options = {'DEFAULT_CLOSED'}
        
        def draw(self, context):
            layout = self.layout
            
            box = layout.box()
            box.label(text="Entropie Quantique", icon='FORCE_VORTEX')
            row = box.row()
            if hasattr(context.scene, 'polyspinor_entropy'):
                row.prop(context.scene, "polyspinor_entropy", text="Niveau")
            
            box = layout.box()
            box.label(text="Corrélations Quantiques", icon='FORCE_HARMONIC')
            box.operator("polyspinor.show_bell_correlations",
                        text="Afficher Corrélations", icon='MESH_GRID')
            box.operator("polyspinor.show_entanglement",
                        text="Afficher Intrication", icon='FORCE_MAGNETIC')
            
            box = layout.box()
            box.label(text="Contrôles de Sécurité", icon='LOCKED')
            if hasattr(context.scene, 'polyspinor_security_enabled'):
                box.prop(context.scene, "polyspinor_security_enabled",
                        text="Vérification Quantique")
            
            box = layout.box()
            box.label(text="Monitoring Quantique", icon='TIME')
            box.operator("polyspinor.refresh_monitoring",
                        text="Rafraîchir", icon='FILE_REFRESH')
            
            if hasattr(context.scene, 'polyspinor_monitoring_status'):
                box.label(text=context.scene.polyspinor_monitoring_status)
            
            layout.separator()
            layout.operator("polyspinor.export_quantum_data",
                           text="Exporter Données", icon='EXPORT')
    
    
    def register():
        """Enregistre les opérateurs et panneaux de visualisation"""
        bpy.utils.register_class(POLYSPINOR_OT_ShowBellCorrelations)
        bpy.utils.register_class(POLYSPINOR_OT_ShowEntanglement)
        bpy.utils.register_class(POLYSPINOR_OT_RefreshMonitoring)
        bpy.utils.register_class(POLYSPINOR_OT_ExportQuantumData)
        bpy.utils.register_class(POLYSPINOR_PT_QuantumVisualization)
    
    
    def unregister():
        """Désenregistre les opérateurs et panneaux"""
        bpy.utils.unregister_class(POLYSPINOR_PT_QuantumVisualization)
        bpy.utils.unregister_class(POLYSPINOR_OT_ExportQuantumData)
        bpy.utils.unregister_class(POLYSPINOR_OT_RefreshMonitoring)
        bpy.utils.unregister_class(POLYSPINOR_OT_ShowEntanglement)
        bpy.utils.unregister_class(POLYSPINOR_OT_ShowBellCorrelations)

else:
    class POLYSPINOR_PT_QuantumVisualization:
        bl_idname = "POLYSPINOR_PT_quantum_visualization"
        bl_label = "Quantum Visualization"
    
    class POLYSPINOR_OT_RefreshMonitoring:
        bl_idname = "polyspinor.refresh_monitoring"
        bl_label = "Refresh Monitoring"
    
    def register():
        pass
    
    def unregister():
        pass
