# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, SUPERUSER_ID, _
import re
from odoo.exceptions import AccessError, UserError
from collections import defaultdict


class MailActivityHistorico(models.Model):


    _name = 'mail.activity.historico'
    _inherits = {'mail.message': 'mail_message_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Histórico de Actividades'


    name = fields.Char(string='Tipo de actividad') 
    res_id = fields.Integer('Related document ID', index=True, required=True)
    res_model_id = fields.Many2one('ir.model', 'Document model', index=True, ondelete='cascade', required=True)
    namemodel = fields.Char(string='Modelo relacionado', related='res_model_id.name') 
    res_model = fields.Char('Related document model', index=True, related='res_model_id.model', store=True, readonly=True)
    res_name = fields.Char('Document Name', compute='_compute_res_name', store=True, help="Display name of the related document.", readonly=True)
    activity_type_id = fields.Many2one('mail.activity.type', 'Activity')
    activity_category = fields.Selection(related='activity_type_id.category', readonly=True)
    activity_decoration = fields.Selection(related='activity_type_id.decoration_type', readonly=True)
    icon = fields.Char('Icon', related='activity_type_id.icon', readonly=True)
    summary = fields.Char('Summary')
    user_id = fields.Many2one('res.users', 'Asignado', default=lambda self: self.env.user, index=True, required=True)
    create_user_id = fields.Many2one('res.users', 'Usuario', default=lambda self: self.env.user, index=True)
    fecha = fields.Date('Fecha', default=fields.Date.today())
    note = fields.Html('Note', sanitize_style=True)
    feedback = fields.Html('FeedBack', sanitize_style=True)




    @api.multi
    def action_open_related_document(self):
        idactivity = self.id        	
        idmodel = self.res_model
        iddestino = self.res_id
        existe = self.env[str(idmodel)].search_count([('id','=',iddestino)])
        print("El contador es: " + str(existe) + "")
        if str(existe) == "0":
           raise AccessError("El Documento Destino ha sido borrado o no se puede acceder a el.")
        namemodel = self.namemodel
        view = {
          'name': _(namemodel),
          'view_type': 'form',
          'view_mode': 'form',
          'res_model': str(idmodel),
          'view_id': False,
          'type': 'ir.actions.act_window',
          'target': 'current',
          'res_id': iddestino }
        return view 




class MailActivity(models.Model):
    """ Mail Activity Mixin is a mixin class to use if you want to add activities
    management on a model. It works like the mail.thread mixin. It defines
    an activity_ids one2many field toward activities using res_id and res_model_id.
    Various related / computed fields are also added to have a global status of
    activities on documents.

    Activities come with a new JS widget for the form view. It is integrated in the
    Chatter widget although it is a separate widget. It displays activities linked
    to the current record and allow to schedule, edit and mark done activities.
    Use widget="mail_activity" on activity_ids field in form view to use it.

    There is also a kanban widget defined. It defines a small widget to integrate
    in kanban vignettes. It allow to manage activities directly from the kanban
    view. Use widget="kanban_activity" on activitiy_ids field in kanban view to
    use it.

    Some context keys allow to control the mixin behavior. Use those in some
    specific cases like import

     * ``mail_activity_automation_skip``: skip activities automation; it means
       no automated activities will be generated, updated or unlinked, allowing
       to save computation and avoid generating unwanted activities;
    """
    _inherit = 'mail.activity'
  
    
    
    setdoneend = fields.Boolean(string='Done / End')    
    res_id2 = fields.Integer(string='resID Hecho')
    res_model_id2 = fields.Many2one('ir.model', 'Model')    
    namemodel = fields.Char(string='Documento origen',related='res_model_id.name')
    
    
    @api.multi
    def creahistorico(self):
        self._check_access('unlink')
        for activity in self:
            if activity.date_deadline <= fields.Date.today():
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', activity.user_id.sudo().partner_id.id),
                    {'type': 'activity_updated', 'activity_deleted': True})

        feedback = self.feedback
        if feedback == False:
           feedback = ""
        else:
           feedback = "\n\n FeedBack: " + str(self.feedback)
        notes = self.note + feedback

        namehistorico = self.env['ir.model'].search([('model', '=', 'mail.activity.historico')], limit=1).id
        resid = self.res_id
        name = self.activity_type_id.name
        res_model_id2 = self.res_model_id.id
        craetehitorico = self.env['mail.activity.historico'].create({
                'name': name,
                'res_id': self.res_id,
                'res_model_id': self.res_model_id.id,
                'res_name': self.res_name,
                'activity_type_id': self.activity_type_id.id,
                'user_id': self.user_id.id,
                'create_user_id': self.env.user.id,
                'summary': self.summary,
                'note': self.note,
                'feedback': self.feedback,
                })
        return craetehitorico



    @api.multi
    def action_done(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback()

    def action_feedback(self, feedback=False):
        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))

        # Search for all attachments linked to the activities we are about to unlink. This way, we
        # can link them to the message posted and prevent their deletion.
        attachments = self.env['ir.attachment'].search_read([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ], ['id', 'res_id'])

        activity_attachments = defaultdict(list)
        for attachment in attachments:
            activity_id = attachment['res_id']
            activity_attachments[activity_id].append(attachment['id'])

        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                mail_activity_type_id=activity.activity_type_id.id,
            )

            # Moving the attachments in the message
            # TODO: Fix void res_id on attachment when you create an activity with an image
            # directly, see route /web_editor/attachment/add
            activity_message = record.message_ids[0]
            message_attachments = self.env['ir.attachment'].browse(activity_attachments[activity.id])
            if message_attachments:
                message_attachments.write({
                    'res_id': activity_message.id,
                    'res_model': activity_message._name,
                })
                activity_message.attachment_ids = message_attachments
            message |= activity_message

        self.creahistorico()
        self.unlink()
        return message.ids and message.ids[0] or False

    @api.multi
    def action_open_related_document(self):
        idactivity = self.id        	
        idmodel = self.res_model
        iddestino = self.res_id
        try:
           contador = self.env[str(idmodel)].search_count([('id', '=', int(iddestino))])        
        except:
           contador = 0
        if idmodel == "mail.entrante" or idmodel == "mail.mail":
           print("\n\n Contador EMAILS: " + str(contador) + "\n\n")
           try:
              contador = self.env[str(idmodel)].search_count([('id', '=', int(iddestino)),('borrado', '=', False)])        
           except:
              contador = 0
        
        if contador == 0:
           raise AccessError("El documento relacionado se ha borrado o no puedes acceder a el")
        view = {
          'name': _('Emails Enviados'),
          'view_type': 'form',
          'view_mode': 'form',
          'res_model': str(idmodel),
          'view_id': False,
          'type': 'ir.actions.act_window',
          'target': 'current',
          'res_id': iddestino }
        return view 






class MailActivityMixin(models.AbstractModel):
    """ Mail Activity Mixin is a mixin class to use if you want to add activities
    management on a model. It works like the mail.thread mixin. It defines
    an activity_ids one2many field toward activities using res_id and res_model_id.
    Various related / computed fields are also added to have a global status of
    activities on documents.

    Activities come with a new JS widget for the form view. It is integrated in the
    Chatter widget although it is a separate widget. It displays activities linked
    to the current record and allow to schedule, edit and mark done activities.
    Use widget="mail_activity" on activity_ids field in form view to use it.

    There is also a kanban widget defined. It defines a small widget to integrate
    in kanban vignettes. It allow to manage activities directly from the kanban
    view. Use widget="kanban_activity" on activitiy_ids field in kanban view to
    use it.

    Some context keys allow to control the mixin behavior. Use those in some
    specific cases like import

     * ``mail_activity_automation_skip``: skip activities automation; it means
       no automated activities will be generated, updated or unlinked, allowing
       to save computation and avoid generating unwanted activities;
    """
    _inherit = 'mail.activity.mixin'
    _description = 'Activity Mixin'
    
    
    
    ## setdoneend = fields.Boolean(string='Done / End')    
    
    

    ### @api.multi
    ### def unlink(self):
    ###     """ Override unlink to delete records activities through (res_model, res_id). """
    ###     record_ids = self.ids
    ###     ### result = super(MailActivityMixin, self).unlink()
    ###     ### self.env['mail.activity'].sudo().search([('res_model', '=', self._name), ('res_id', 'in', record_ids)]).unlink()
    ###     result = super(MailActivityMixin, self).write({'setdoneend': True})
    ###     return result




### ### 

    