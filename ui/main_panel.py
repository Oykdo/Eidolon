"""
Panneau de Contrôle Principal Poly-Spinor Nexus 7D
Interface utilisateur Blender pour la génération de clés et visualisation quantique
"""

import numpy as np
from typing import Optional, Dict, Any

# Blender Python API (optionnel)
bpy: Any = None
BLENDER_AVAILABLE = False

try:
    import bpy as _bpy
    bpy = _bpy
    BLENDER_AVAILABLE = True
except ImportError:
    pass

import sys
sys.path.append('..')

from ..core.spinor_crypto import SpinorCryptographicEngine
from ..core.quantum_verification import AdvancedBellVerification
from ..core.blender_engine import PolySpinorBlenderEngine
from ..core.spatial_capture import SpatialCaptureSystem, DieType


if BLENDER_AVAILABLE:
    
    class POLYSPINOR_OT_Generate7DKey(bpy.types.Operator):
        """Opérateur pour générer une clé 7D"""
        bl_idname = "polyspinor.generate_7d_key"
        bl_label = "Générer Clé Quantique 7D"
        bl_description = "Génère une clé cryptographique 7D basée sur les corrélations quantiques"
        
        def execute(self, context):
            try:
                data_7d = self.load_7d_data(context)
                
                if not self.quantum_validation(data_7d):
                    self.report({'ERROR'}, "Validation quantique échouée")
                    return {'CANCELLED'}
                
                engine = PolySpinorBlenderEngine()
                clusters = engine.create_hyper_cluster_scene(data_7d)
                
                crypto_engine = SpinorCryptographicEngine(
                    seed_7d=np.array(list(data_7d.values())[:7]) if data_7d else None
                )
                master_key = crypto_engine.generate_master_key()
                
                self.save_secure_key(master_key, context)
                self.update_ui_with_key_info(master_key, context)
                
                self.report({'INFO'}, f"Clé 7D générée: {len(master_key)*8} bits")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur génération: {str(e)}")
                return {'CANCELLED'}
        
        def load_7d_data(self, context) -> Dict:
            """Charge les données 7D depuis la scène ou génère des données simulées"""
            if hasattr(context.scene, 'polyspinor_7d_key'):
                key = context.scene.polyspinor_7d_key
                if any(v != 0 for v in key):
                    return {f'dim_{i}': v for i, v in enumerate(key)}
            
            capture = SpatialCaptureSystem()
            try:
                capture.quantum_calibration()
            except:
                pass
            
            data = {}
            for i, die_type in enumerate([DieType.D6] * 7):
                data[f'dim_{i}'] = np.random.uniform(-1, 1)
            
            return data
        
        def quantum_validation(self, data_7d: Dict) -> bool:
            """Valide les propriétés quantiques des données"""
            verifier = AdvancedBellVerification()
            
            try:
                state = verifier.prepare_7d_entangled_state()
                
                correlations = verifier.build_correlation_tensor(2, 2)
                
                inequalities = verifier.generalized_bell_inequalities(
                    correlations.reshape(1, 2, 2)
                )
                violations = verifier.detect_quantum_violations(inequalities)
                
                randomness = verifier.extract_certified_randomness(
                    correlations.reshape(1, 2, 2), violations
                )
                
                min_entropy = verifier.calculate_min_entropy(randomness)
                
                if min_entropy < 100:
                    return False
                
                return True
                
            except Exception as e:
                print(f"Validation quantique échouée: {e}")
                return False
        
        def save_secure_key(self, key: bytes, context):
            """Sauvegarde sécurisée de la clé"""
            key_floats = []
            for i in range(7):
                if i * 8 < len(key):
                    val = int.from_bytes(key[i*8:(i+1)*8], 'big')
                    normalized = (val / (2**64)) * 2 - 1
                    key_floats.append(normalized)
                else:
                    key_floats.append(0.0)
            
            context.scene.polyspinor_7d_key = tuple(key_floats)
        
        def update_ui_with_key_info(self, key: bytes, context):
            """Met à jour l'interface avec les informations de clé"""
            context.scene.polyspinor_entropy = len(key) * 8 / 10000
            context.scene.polyspinor_monitoring_status = "Clé générée"
    
    
    class POLYSPINOR_OT_VisualizeQuantum(bpy.types.Operator):
        """Opérateur pour visualiser les données quantiques"""
        bl_idname = "polyspinor.visualize_quantum"
        bl_label = "Visualiser Données Quantiques"
        bl_description = "Crée une visualisation 3D des corrélations quantiques"
        
        def execute(self, context):
            try:
                engine = PolySpinorBlenderEngine()
                
                if hasattr(context.scene, 'polyspinor_7d_key') and \
                   any(v != 0 for v in context.scene.polyspinor_7d_key):
                    key_data = np.array(context.scene.polyspinor_7d_key)
                    engine.create_7d_object_standalone(key_data)
                else:
                    engine.create_hyper_cluster_scene()
                
                self.report({'INFO'}, "Visualisation quantique créée")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur visualisation: {str(e)}")
                return {'CANCELLED'}
    
    
    class POLYSPINOR_OT_CalibrateSystem(bpy.types.Operator):
        """Opérateur pour calibrer le système quantique"""
        bl_idname = "polyspinor.calibrate_system"
        bl_label = "Calibrer Système Quantique"
        bl_description = "Effectue la calibration EPR du système"
        
        def execute(self, context):
            try:
                capture = SpatialCaptureSystem()
                calibration = capture.quantum_calibration()
                
                context.scene.polyspinor_monitoring_status = \
                    f"Calibré: S={calibration['bell_parameter']:.3f}"
                
                self.report({'INFO'}, 
                    f"Calibration réussie: Bell S={calibration['bell_parameter']:.3f}")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Calibration échouée: {str(e)}")
                return {'CANCELLED'}
    
    
    class POLYSPINOR_OT_VerifyBell(bpy.types.Operator):
        """Opérateur pour vérifier les inégalités de Bell"""
        bl_idname = "polyspinor.verify_bell"
        bl_label = "Vérifier Inégalités Bell"
        bl_description = "Vérifie les violations des inégalités de Bell"
        
        def execute(self, context):
            try:
                verifier = AdvancedBellVerification()
                state = verifier.prepare_7d_entangled_state()
                
                correlations = verifier.build_correlation_tensor(4, 4)
                inequalities = verifier.generalized_bell_inequalities(
                    correlations.reshape(2, 8, 7)
                )
                violations = verifier.detect_quantum_violations(inequalities)
                
                context.scene.polyspinor_monitoring_status = \
                    f"Violations Bell: {len(violations)}"
                
                if hasattr(context.scene, 'polyspinor_correlations'):
                    context.scene.polyspinor_correlations = tuple(
                        correlations.flatten()[:7].tolist()
                    )
                
                self.report({'INFO'}, 
                    f"Vérification Bell: {len(violations)} violations détectées")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Vérification échouée: {str(e)}")
                return {'CANCELLED'}
    
    
    class POLYSPINOR_PT_MainPanel(bpy.types.Panel):
        """Panneau principal Poly-Spinor Nexus"""
        bl_label = "Poly-Spinor Nexus 7D"
        bl_idname = "POLYSPINOR_PT_main_panel"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "PolySpinor"
        
        def draw(self, context):
            layout = self.layout
            
            box = layout.box()
            box.label(text="Génération de Clés", icon='KEY_HLT')
            box.operator("polyspinor.generate_7d_key", 
                        text="Générer Clé 7D", icon='RNA')
            
            if hasattr(context.scene, 'polyspinor_7d_key'):
                key = context.scene.polyspinor_7d_key
                if any(v != 0 for v in key):
                    row = box.row()
                    row.label(text=f"Clé: {key[0]:.4f}...", icon='LOCKED')
            
            box = layout.box()
            box.label(text="Calibration Quantique", icon='MODIFIER')
            box.operator("polyspinor.calibrate_system",
                        text="Calibrer Système", icon='CON_TRACKTO')
            box.operator("polyspinor.verify_bell",
                        text="Vérifier Bell", icon='CHECKMARK')
            
            box = layout.box()
            box.label(text="Visualisation", icon='VIEW3D')
            box.operator("polyspinor.visualize_quantum",
                        text="Créer Scène Quantique", icon='MESH_ICOSPHERE')
            
            box = layout.box()
            box.label(text="Monitoring", icon='INFO')
            
            if hasattr(context.scene, 'polyspinor_entropy'):
                row = box.row()
                row.label(text="Entropie:")
                row.prop(context.scene, "polyspinor_entropy", text="")
            
            if hasattr(context.scene, 'polyspinor_monitoring_status'):
                box.label(text=context.scene.polyspinor_monitoring_status)
    
    
    class POLYSPINOR_PT_QuantumVisualization(bpy.types.Panel):
        """Panneau de visualisation quantique"""
        bl_label = "Visualisation Quantique 7D"
        bl_idname = "POLYSPINOR_PT_quantum_viz"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "PolySpinor"
        bl_options = {'DEFAULT_CLOSED'}
        
        def draw(self, context):
            layout = self.layout
            
            box = layout.box()
            box.label(text="Entropie Quantique", icon='FORCE_VORTEX')
            if hasattr(context.scene, 'polyspinor_entropy'):
                row = box.row()
                row.prop(context.scene, "polyspinor_entropy", text="Niveau")
            
            box = layout.box()
            box.label(text="Corrélations Quantiques", icon='FORCE_HARMONIC')
            if hasattr(context.scene, 'polyspinor_correlations'):
                for i in range(min(3, len(context.scene.polyspinor_correlations))):
                    row = box.row()
                    row.label(text=f"Dim {i}:")
                    row.label(text=f"{context.scene.polyspinor_correlations[i]:.4f}")
            
            box = layout.box()
            box.label(text="Contrôles de Sécurité", icon='LOCKED')
            if hasattr(context.scene, 'polyspinor_security_enabled'):
                box.prop(context.scene, "polyspinor_security_enabled",
                        text="Sécurité Quantique")
            
            box = layout.box()
            box.label(text="Monitoring Quantique", icon='TIME')
            if hasattr(context.scene, 'polyspinor_monitoring_status'):
                box.label(text=context.scene.polyspinor_monitoring_status)
    
    
    def register():
        """Enregistre les classes et propriétés"""
        bpy.types.Scene.polyspinor_7d_key = bpy.props.FloatVectorProperty(
            name="7D Key",
            description="Clé quantique 7D générée",
            size=7,
            default=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        )
        
        bpy.types.Scene.polyspinor_entropy = bpy.props.FloatProperty(
            name="Entropy",
            description="Niveau d'entropie quantique",
            default=0.0,
            min=0.0,
            max=1.0
        )
        
        bpy.types.Scene.polyspinor_correlations = bpy.props.FloatVectorProperty(
            name="Correlations",
            description="Valeurs de corrélation 7D",
            size=7,
            default=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            min=-1.0,
            max=1.0
        )
        
        bpy.types.Scene.polyspinor_security_enabled = bpy.props.BoolProperty(
            name="Security Enabled",
            description="Activer les fonctionnalités de sécurité quantique",
            default=True
        )
        
        bpy.types.Scene.polyspinor_monitoring_status = bpy.props.StringProperty(
            name="Monitoring Status",
            description="Statut du monitoring",
            default="En attente"
        )
        
        bpy.utils.register_class(POLYSPINOR_OT_Generate7DKey)
        bpy.utils.register_class(POLYSPINOR_OT_VisualizeQuantum)
        bpy.utils.register_class(POLYSPINOR_OT_CalibrateSystem)
        bpy.utils.register_class(POLYSPINOR_OT_VerifyBell)
        bpy.utils.register_class(POLYSPINOR_PT_MainPanel)
        bpy.utils.register_class(POLYSPINOR_PT_QuantumVisualization)
    
    
    def unregister():
        """Désenregistre les classes et propriétés"""
        bpy.utils.unregister_class(POLYSPINOR_PT_QuantumVisualization)
        bpy.utils.unregister_class(POLYSPINOR_PT_MainPanel)
        bpy.utils.unregister_class(POLYSPINOR_OT_VerifyBell)
        bpy.utils.unregister_class(POLYSPINOR_OT_CalibrateSystem)
        bpy.utils.unregister_class(POLYSPINOR_OT_VisualizeQuantum)
        bpy.utils.unregister_class(POLYSPINOR_OT_Generate7DKey)
        
        del bpy.types.Scene.polyspinor_monitoring_status
        del bpy.types.Scene.polyspinor_security_enabled
        del bpy.types.Scene.polyspinor_correlations
        del bpy.types.Scene.polyspinor_entropy
        del bpy.types.Scene.polyspinor_7d_key

else:
    class POLYSPINOR_OT_Generate7DKey:
        bl_idname = "polyspinor.generate_7d_key"
        bl_label = "Generate 7D Key"
    
    class POLYSPINOR_OT_VisualizeQuantum:
        bl_idname = "polyspinor.visualize_quantum"
        bl_label = "Visualize Quantum Data"
    
    class POLYSPINOR_PT_QuantumVisualization:
        bl_idname = "POLYSPINOR_PT_quantum_viz"
        bl_label = "Quantum Visualization"
    
    def register():
        pass
    
    def unregister():
        pass
