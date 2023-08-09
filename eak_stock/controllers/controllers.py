# -*- coding: utf-8 -*-
# from odoo import http


# class EakStock(http.Controller):
#     @http.route('/eak_stock/eak_stock', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/eak_stock/eak_stock/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('eak_stock.listing', {
#             'root': '/eak_stock/eak_stock',
#             'objects': http.request.env['eak_stock.eak_stock'].search([]),
#         })

#     @http.route('/eak_stock/eak_stock/objects/<model("eak_stock.eak_stock"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('eak_stock.object', {
#             'object': obj
#         })
