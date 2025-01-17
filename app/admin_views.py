from flask import render_template, request, redirect, jsonify, make_response, url_for, session, flash, Blueprint
from flask_login import login_required, current_user
from . import db
from app import app
from .models import Request
from .email_template import request_approved_template, documents_approved_template, documents_available_template
import shutil

from datetime import date

from docxtpl import DocxTemplate
from docx2pdf import convert
import ast 

from send_email import send_message

from .Lists import Documents

import pythoncom

admin_views = Blueprint('admin_views', __name__)

@admin_views.route("/admin/dashboard")
@login_required
def admin_dashboard():
    requests = Request.query.all()
    return render_template("admin/dashboard.html", requests = requests, documents = Documents, user = current_user)

@admin_views.route("/sort_by_date")
@login_required
def sort_by_date():
    requests = Request.query.order_by(Request.date_of_request.desc()).all()
    return render_template("admin/dashboard.html", requests = requests, documents = Documents, user = current_user)

@admin_views.route("/sort_by_document/<document>")
@login_required
def sort_by_document(document):
    requests = Request.query.all()
    new_list = list()
    for request in requests:
        if document in request.requested_documents:
            new_list.append(request)

    return render_template("admin/dashboard.html", requests = new_list, documents = Documents, user = current_user)

@admin_views.route("/update/<int:queue_number>/<classification>")
@login_required
def update(queue_number, classification):
    query = Request.query.get_or_404(queue_number)  
    try:
        if classification == "request_approved":
            send_message("scvizconde@up.edu.ph", 
                query.email, 
                f"Request approved for order number { query.queue_number }", 
                request_approved_template(query.first_name, query.queue_number)) 
            query.request_approved = True
        elif classification == "documents_approved":
            send_message("scvizconde@up.edu.ph", 
                query.email, 
                f"Documents approved for order number { query.queue_number }", 
                documents_approved_template(query.first_name, query.queue_number))
            query.documents_approved = True
        else:
            send_message("scvizconde@up.edu.ph", 
                query.email, 
                f"order number { query.queue_number } available for claiming", 
                documents_available_template(query.first_name, query.queue_number))
            query.request_available = True

        db.session.commit()
        flash("Successfully sent update email", "success")
        return redirect(url_for("admin_views.admin_dashboard"))
    except:
        flash("error sending update email", "error")
        return redirect(url_for("admin_views.admin_dashboard"))

@admin_views.route("/delete/<int:queue_number>")
@login_required
def delete_entry(queue_number):
    query = Request.query.get_or_404(queue_number)  
    folder_name =" ".join([query.first_name.upper(), query.middle_name.upper(), query.last_name.upper()])
    folder_path = app.config["FILE_UPLOADS"] + "/" + folder_name

    price_map = query.price_map
    price_dictionary = ast.literal_eval(price_map)

    invoice_list = [[1, k, int(v)] for k, v in price_dictionary.items()]
    
    doc = DocxTemplate("app/invoice_template.docx")

    try:
        doc.render({
            "name" : folder_name,
            "student_number" : query.student_number,
            "date" : date.today(),
            "invoice_list" : invoice_list,
            "total" : sum(v[2] for v in invoice_list)
        })

        docxpath = folder_path + "/" + query.last_name + ".docx"
        pdfpath = folder_path + "/" + query.last_name + ".pdf"
        doc.save(docxpath)
        pythoncom.CoInitialize()
        convert(docxpath, pdfpath)

        send_message("scvizconde@up.edu.ph", 
                    query.email, 
                    f'Receipt for order number {query.queue_number}', 
                    "test content", 
                    [pdfpath])

        shutil.rmtree(folder_path, ignore_errors = False)

        db.session.delete(query)
        db.session.commit()
        flash("Transaction successfully deleted", "success")
        return redirect(url_for("admin_views.admin_dashboard"))
    except:
        flash("Error deleting transaction", "error")
        return redirect(url_for("admin_views.admin_dashboard"))





@admin_views.route("/remove/<int:queue_number>")
@login_required
def remove_entry(queue_number):
    query = Request.query.get_or_404(queue_number)  
    folder_name =" ".join([query.first_name.upper(), query.middle_name.upper(), query.last_name.upper()])
    folder_path = app.config["FILE_UPLOADS"] + "/" + folder_name

    try:
        shutil.rmtree(folder_path, ignore_errors = False)

        db.session.delete(query)
        db.session.commit()
        flash("Entry successfully deleted", "success")
        return redirect(url_for("admin_views.admin_dashboard"))
    except:
        flash("Error deleting transaction", "error")
        return redirect(url_for("admin_views.admin_dashboard"))


