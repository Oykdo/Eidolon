"""
Interface d'Entiercement Blender
Panneau pour le dépôt, récupération et vérification de documents
"""

import json
import numpy as np
from typing import Dict, Optional, Any
from datetime import datetime

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

from ..protocols.document_escrow import (
    PolySpinorEscrow7D,
    QuantumIntegrityVerifier
)
from ..protocols.recovery_protocol import (
    QuantumRecoveryProtocol,
    EmergencyRecoveryProtocol
)


escrow_system = PolySpinorEscrow7D()
integrity_verifier = QuantumIntegrityVerifier()
recovery_protocol = QuantumRecoveryProtocol()


if BLENDER_AVAILABLE:
    
    class POLYSPINOR_OT_DepositDocument(bpy.types.Operator):
        """Opérateur pour déposer un document en entiercement"""
        bl_idname = "polyspinor.deposit_document"
        bl_label = "Déposer Document"
        bl_description = "Entrepose un document avec sceau spinorial 7D"
        
        filepath: bpy.props.StringProperty(
            subtype='FILE_PATH',
            description="Chemin vers le document à entreposer"
        )
        
        def execute(self, context):
            global escrow_system
            
            try:
                with open(self.filepath, 'rb') as f:
                    document_data = f.read()
                
                clusters = self._get_scene_clusters(context)
                
                receipt = escrow_system.escrow_document_data(
                    document_data, clusters
                )
                
                self._save_receipt(context, receipt)
                
                if hasattr(context.scene, 'polyspinor_monitoring_status'):
                    context.scene.polyspinor_monitoring_status = \
                        f"Document entreposé: {receipt.escrow_id}"
                
                self.report({'INFO'}, 
                    f"Document entreposé avec ID: {receipt.escrow_id}")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur dépôt: {str(e)}")
                return {'CANCELLED'}
        
        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        
        def _get_scene_clusters(self, context) -> list:
            """Récupère les clusters de la scène"""
            clusters = []
            for collection in bpy.data.collections:
                if collection.name.startswith("Cluster_"):
                    clusters.append({
                        'name': collection.name,
                        'objects': list(collection.objects)
                    })
            return clusters
        
        def _save_receipt(self, context, receipt):
            """Sauvegarde le reçu dans les propriétés de scène"""
            if hasattr(context.scene, 'polyspinor_escrow_receipts_json'):
                try:
                    receipts = json.loads(
                        context.scene.polyspinor_escrow_receipts_json
                    )
                except:
                    receipts = {}
                
                receipts[receipt.escrow_id] = receipt.to_dict()
                context.scene.polyspinor_escrow_receipts_json = json.dumps(receipts)
    
    
    class POLYSPINOR_OT_RetrieveDocument(bpy.types.Operator):
        """Opérateur pour récupérer un document entreposé"""
        bl_idname = "polyspinor.retrieve_document"
        bl_label = "Récupérer Document"
        bl_description = "Récupère un document entreposé"
        
        escrow_id: bpy.props.StringProperty(
            name="ID Escrow",
            description="Identifiant de l'entiercement"
        )
        
        output_path: bpy.props.StringProperty(
            subtype='FILE_PATH',
            name="Chemin de sortie",
            description="Où sauvegarder le document récupéré"
        )
        
        def execute(self, context):
            global escrow_system
            
            try:
                document_data = escrow_system.retrieve_document(
                    self.escrow_id, conditions_met=True
                )
                
                if document_data is None:
                    self.report({'ERROR'}, "Conditions non remplies")
                    return {'CANCELLED'}
                
                with open(self.output_path, 'wb') as f:
                    f.write(document_data)
                
                if hasattr(context.scene, 'polyspinor_monitoring_status'):
                    context.scene.polyspinor_monitoring_status = \
                        f"Document récupéré: {self.escrow_id}"
                
                self.report({'INFO'}, f"Document récupéré: {self.output_path}")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur récupération: {str(e)}")
                return {'CANCELLED'}
        
        def invoke(self, context, event):
            return context.window_manager.invoke_props_dialog(self)
        
        def draw(self, context):
            layout = self.layout
            layout.prop(self, "escrow_id")
            layout.prop(self, "output_path")
    
    
    class POLYSPINOR_OT_VerifyIntegrity(bpy.types.Operator):
        """Opérateur pour vérifier l'intégrité d'un escrow"""
        bl_idname = "polyspinor.verify_integrity"
        bl_label = "Vérifier Intégrité"
        bl_description = "Vérifie l'intégrité quantique d'un document entreposé"
        
        escrow_id: bpy.props.StringProperty(
            name="ID Escrow",
            description="Identifiant de l'entiercement à vérifier"
        )
        
        def execute(self, context):
            global escrow_system, integrity_verifier
            
            try:
                audit_report = integrity_verifier.perform_quantum_audit(
                    self.escrow_id, escrow_system
                )
                
                if hasattr(context.scene, 'polyspinor_monitoring_status'):
                    status = "Intégrité OK" if audit_report['integrity_verified'] else "Intégrité COMPROMIS"
                    context.scene.polyspinor_monitoring_status = \
                        f"{status} | Sceau: {'OK' if audit_report['seal_verified'] else 'INVALIDE'}"
                
                if audit_report['integrity_verified'] and audit_report['seal_verified']:
                    self.report({'INFO'}, 
                        f"Intégrité vérifiée pour {self.escrow_id}")
                else:
                    violations = ", ".join(audit_report['violations_detected'])
                    self.report({'WARNING'}, 
                        f"Violations détectées: {violations}")
                
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur vérification: {str(e)}")
                return {'CANCELLED'}
        
        def invoke(self, context, event):
            return context.window_manager.invoke_props_dialog(self)
        
        def draw(self, context):
            layout = self.layout
            layout.prop(self, "escrow_id")
    
    
    class POLYSPINOR_OT_RecoverDocument(bpy.types.Operator):
        """Opérateur pour la récupération quantique"""
        bl_idname = "polyspinor.recover_document"
        bl_label = "Récupération Quantique"
        bl_description = "Récupère un document via protocole quantique sécurisé"
        
        escrow_id: bpy.props.StringProperty(
            name="ID Escrow",
            description="Identifiant de l'entiercement"
        )
        
        output_path: bpy.props.StringProperty(
            subtype='FILE_PATH',
            name="Chemin de sortie"
        )
        
        def execute(self, context):
            global escrow_system, recovery_protocol
            
            try:
                token, witness = recovery_protocol.initiate_recovery(
                    self.escrow_id, escrow_system
                )
                
                document_data = recovery_protocol.recover_escrowed_document(
                    token, witness, escrow_system
                )
                
                with open(self.output_path, 'wb') as f:
                    f.write(document_data)
                
                if hasattr(context.scene, 'polyspinor_monitoring_status'):
                    context.scene.polyspinor_monitoring_status = \
                        f"Récupération quantique réussie: {self.escrow_id}"
                
                self.report({'INFO'}, 
                    f"Document récupéré via protocole quantique: {self.output_path}")
                return {'FINISHED'}
                
            except Exception as e:
                self.report({'ERROR'}, f"Erreur récupération quantique: {str(e)}")
                return {'CANCELLED'}
        
        def invoke(self, context, event):
            return context.window_manager.invoke_props_dialog(self)
        
        def draw(self, context):
            layout = self.layout
            layout.prop(self, "escrow_id")
            layout.prop(self, "output_path")
    
    
    class POLYSPINOR_OT_ListEscrows(bpy.types.Operator):
        """Liste les escrows disponibles"""
        bl_idname = "polyspinor.list_escrows"
        bl_label = "Lister Escrows"
        bl_description = "Affiche la liste des documents entreposés"
        
        def execute(self, context):
            global escrow_system
            
            escrow_list = list(escrow_system.escrow_store.keys())
            
            if escrow_list:
                message = f"Escrows: {', '.join(escrow_list[:5])}"
                if len(escrow_list) > 5:
                    message += f"... (+{len(escrow_list)-5})"
            else:
                message = "Aucun document entreposé"
            
            if hasattr(context.scene, 'polyspinor_monitoring_status'):
                context.scene.polyspinor_monitoring_status = message
            
            self.report({'INFO'}, message)
            return {'FINISHED'}
    
    
    class POLYSPINOR_PT_EscrowPanel(bpy.types.Panel):
        """Panneau d'entiercement de documents"""
        bl_label = "Entiercement 7D"
        bl_idname = "POLYSPINOR_PT_escrow_panel"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "PolySpinor"
        bl_options = {'DEFAULT_CLOSED'}
        
        def draw(self, context):
            layout = self.layout
            
            box = layout.box()
            box.label(text="Dépôt de Documents", icon='IMPORT')
            box.operator("polyspinor.deposit_document",
                        text="Déposer Document", icon='FILE_NEW')
            
            box = layout.box()
            box.label(text="Récupération", icon='EXPORT')
            box.operator("polyspinor.retrieve_document",
                        text="Récupérer Document", icon='FILE')
            box.operator("polyspinor.recover_document",
                        text="Récupération Quantique", icon='PHYSICS')
            
            box = layout.box()
            box.label(text="Vérification", icon='CHECKMARK')
            box.operator("polyspinor.verify_integrity",
                        text="Vérifier Intégrité", icon='VIEWZOOM')
            box.operator("polyspinor.list_escrows",
                        text="Lister Escrows", icon='LINENUMBERS_ON')
            
            box = layout.box()
            box.label(text="Statut", icon='INFO')
            
            escrow_count = len(escrow_system.escrow_store)
            box.label(text=f"Documents entreposés: {escrow_count}")
            
            if hasattr(context.scene, 'polyspinor_monitoring_status'):
                status = context.scene.polyspinor_monitoring_status
                if len(status) > 40:
                    status = status[:37] + "..."
                box.label(text=status)
    
    
    def register():
        """Enregistre les opérateurs et panneaux d'entiercement"""
        bpy.utils.register_class(POLYSPINOR_OT_DepositDocument)
        bpy.utils.register_class(POLYSPINOR_OT_RetrieveDocument)
        bpy.utils.register_class(POLYSPINOR_OT_VerifyIntegrity)
        bpy.utils.register_class(POLYSPINOR_OT_RecoverDocument)
        bpy.utils.register_class(POLYSPINOR_OT_ListEscrows)
        bpy.utils.register_class(POLYSPINOR_PT_EscrowPanel)
    
    
    def unregister():
        """Désenregistre les opérateurs et panneaux"""
        bpy.utils.unregister_class(POLYSPINOR_PT_EscrowPanel)
        bpy.utils.unregister_class(POLYSPINOR_OT_ListEscrows)
        bpy.utils.unregister_class(POLYSPINOR_OT_RecoverDocument)
        bpy.utils.unregister_class(POLYSPINOR_OT_VerifyIntegrity)
        bpy.utils.unregister_class(POLYSPINOR_OT_RetrieveDocument)
        bpy.utils.unregister_class(POLYSPINOR_OT_DepositDocument)

else:
    class POLYSPINOR_OT_DepositDocument:
        bl_idname = "polyspinor.deposit_document"
        bl_label = "Deposit Document"
    
    class POLYSPINOR_OT_RetrieveDocument:
        bl_idname = "polyspinor.retrieve_document"
        bl_label = "Retrieve Document"
    
    class POLYSPINOR_OT_VerifyIntegrity:
        bl_idname = "polyspinor.verify_integrity"
        bl_label = "Verify Integrity"
    
    class POLYSPINOR_OT_RecoverDocument:
        bl_idname = "polyspinor.recover_document"
        bl_label = "Recover Document"
    
    class POLYSPINOR_PT_EscrowPanel:
        bl_idname = "POLYSPINOR_PT_escrow_panel"
        bl_label = "Escrow Panel"
    
    def register():
        pass
    
    def unregister():
        pass
