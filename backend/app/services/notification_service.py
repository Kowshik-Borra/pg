from app.extensions import db
from app.models.governance import Notification

def send_notification(user_id: int, title: str, message: str, notification_type: str = "SYSTEM", entity_type: str = None, entity_id: int = None):
    """
    Standardized in-app notification creator.
    """
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_entity_type=entity_type,
            related_entity_id=entity_id
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        print(f"Warning: Failed to create notification: {e}")
        return None

