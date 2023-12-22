from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from website.models import Artifact, Talk, Publication, Poster, Grant
from wand.image import Image, Color
from django.conf import settings
import os
from django.core.files import File
import website.utils.fileutils as ml_fileutils

import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

#
# A note about the @receiver decorator used in signals.py.
# There are two ways to hook up receiver functions
# 1. You can hook them up manually:
#     from django.core.signals import request_finished
#     request_finished.connect(my_callback)
#
# 2. You can use a receiver() decorator (the @receiver construct). This is the approach we are using.
#    In order for this to work, we must add in an import website.signals to the ready() function
#    in apps.py, which we've done.
# See : https://docs.djangoproject.com/en/1.9/topics/signals/#receiver-functions
#

@receiver(m2m_changed, sender=Grant.authors.through)
@receiver(m2m_changed, sender=Poster.authors.through)
@receiver(m2m_changed, sender=Talk.authors.through)
@receiver(m2m_changed, sender=Publication.authors.through)
def authors_changed(sender, instance, action, reverse, **kwargs):
    """
    Signal receiver for changes in the 'authors' field of Poster, Talk, and Publication models.

    This function is triggered when the 'authors' field of an instance of any of the above models is modified.
    It checks if the filenames of the instance need to be updated whenever authors are added and the change is not a reverse relation.

    Parameters:
    sender (Model): The model class that the authors field belongs to. It could be Poster, Talk, or Publication.
    instance (Model instance): The actual instance of the sender model class that is being modified.
    action (str): The type of operation performed on the many-to-many field. It can be one of the following:
                  - "pre_add": Sent before one or more objects are added to the relation.
                  - "post_add": Sent after one or more objects have been added to the relation.
                  - "pre_remove": Sent before one or more objects are removed from the relation.
                  - "post_remove": Sent after one or more objects have been removed from the relation.
                  - "pre_clear": Sent before the relation is cleared.
                  - "post_clear": Sent after the relation has been cleared.
    reverse (bool): A flag indicating the direction of the relation:
                    - If `False`, the modification was made from the instance side.
                    - If `True`, the modification was made from the related object side.
    **kwargs: Additional keyword arguments.

    Returns:
    None
    """
    _logger.debug(
        f"Started authors_changed with sender={sender}, instance={instance}, "
        f"action={action}, reverse={reverse}, and kwargs={kwargs}"
    )
    
    if action == 'post_add' and not reverse:
        # The authors field is a many-to-many field, which is handled differently than other fields in Django
        # When an artifact object is first created and save called (to save the object back to the database),
        # the authors field is not yet set. It won't be set until after super.save() is completed the first time
        # So, we use this authors_changed signal to both listen for when the assigned author is
        # initially setup and for when it is changed (e.g., if the first author changes)
        if Artifact.do_filenames_need_updating(instance):
            _logger.debug("Filenames need to be updated, calling instance.save()")
            instance.save()

    _logger.debug(f"Completed authors_changed")

    
@receiver(post_save, sender=Talk)
def talk_post_save(sender, **kwargs):
    """
    This function is a Django signal receiver that gets called after a `Talk` instance is saved.
    It logs the start and end of the function execution, as well as the speakers of the talk.

    Parameters:
    sender (ModelBase): The model class. `Talk` in this case.
    **kwargs: Arbitrary keyword arguments. This function expects 'instance' to be one of the keywords.
        - instance (Model instance): The actual instance of the model that just got saved.
        - created (bool): True if a new record was created, False if an existing record was saved.
        - raw (bool): True if the model is saved exactly as presented (i.e., when loading a fixture). 
          One should not query/modify other records in the database as the database might not be in a consistent state yet.
        - update_fields (set): The set of fields to update as passed to Model.save(), or None if 
          the update_fields argument wasn't passed to save().
    """
    _logger.debug(f"Started talk_post_save with sender={sender} and kwargs={kwargs}")

    # Note to the reader:
    # I considered putting the talk file renaming code (currently in Talk.save()) here; however,
    # this proved impossible because talk_post_save is called before Talk.speakers_changed and so
    # we can't get access to the speaker (as a many-to-many foreign field) until after speakers_changed
    # I just wanted to add this note for rationale for *why* it's not here in case a future brain 
    # thinks it would be a better fit here.
    #
    # Note also that we used to do our PDF thumbnail generation here but I consolidated it
    # in talk.save() to keep all of this code in one place
  
    talk = kwargs['instance']
    _logger.debug(f"Speakers: {talk.authors.all()}")

    _logger.debug(f"Completed talk_post_save with sender={sender} and kwargs={kwargs}")