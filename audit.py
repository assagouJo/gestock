from sqlalchemy import event
from flask_login import current_user
from flask import has_request_context
from datetime import datetime
from app import db
from models import Log


# ==========================================
# LISTENER AUTOMATIQUE AVANT FLUSH
# ==========================================

@event.listens_for(db.session, "before_flush")
def receive_before_flush(session, flush_context, instances):

    # INSERT
    for obj in session.new:
        create_audit_log(session, obj, "INSERT")

    # UPDATE
    for obj in session.dirty:
        if session.is_modified(obj, include_collections=False):
            create_audit_log(session, obj, "UPDATE")

    # DELETE
    for obj in session.deleted:
        create_audit_log(session, obj, "DELETE")


# ==========================================
# FONCTION CREATION LOG
# ==========================================

def create_audit_log(session, obj, action):

    # ❌ Ne jamais logger la table Log elle-même
    if isinstance(obj, Log):
        return

    # ❌ Si l'objet n'a pas d'id
    if not hasattr(obj, "id"):
        return

    # Récupération utilisateur
    user_id = None
    username = "System"

    if has_request_context() and current_user.is_authenticated:
        user_id = current_user.id
        username = current_user.username

    # Création du log (CORRIGÉ)
    log = Log(
        user_id=user_id,
        username=username,
        action=action,
        table_name=obj.__tablename__,
        record_id=getattr(obj, "id", None),
        created_at=datetime.utcnow()   # ✅ VALEUR RÉELLE, PAS Column
    )

    session.add(log)