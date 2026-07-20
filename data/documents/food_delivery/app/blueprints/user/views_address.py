"""User address management views."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.user import user_bp
from app.blueprints.user.forms import AddressForm
from app.models.address import Address
from app.utils.decorators import role_required


@user_bp.route('/addresses')
@login_required
@role_required('user')
def addresses():
    addresses = Address.query.filter_by(user_id=current_user.id).order_by(
        Address.is_default.desc(), Address.created_at.desc()).all()
    return render_template('addresses.html', addresses=addresses)


@user_bp.route('/addresses/add', methods=['POST'])
@login_required
@role_required('user')
def address_add():
    form = AddressForm()
    if form.validate_on_submit():
        addr = Address(
            user_id=current_user.id,
            label=form.label.data,
            address_detail=form.address_detail.data,
        )
        db.session.add(addr)
        db.session.commit()
        flash('地址已添加', 'success')
    return redirect(url_for('user.addresses'))


@user_bp.route('/addresses/edit/<int:addr_id>', methods=['POST'])
@login_required
@role_required('user')
def address_edit(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.addresses'))
    form = AddressForm()
    if form.validate_on_submit():
        addr.label = form.label.data
        addr.address_detail = form.address_detail.data
        db.session.commit()
        flash('地址已更新', 'success')
    return redirect(url_for('user.addresses'))


@user_bp.route('/addresses/delete/<int:addr_id>', methods=['POST'])
@login_required
@role_required('user')
def address_delete(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.addresses'))
    db.session.delete(addr)
    db.session.commit()
    flash('地址已删除', 'info')
    return redirect(url_for('user.addresses'))


@user_bp.route('/addresses/default/<int:addr_id>', methods=['POST'])
@login_required
@role_required('user')
def address_set_default(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.addresses'))
    Address.query.filter_by(user_id=current_user.id).update({'is_default': False})
    addr.is_default = True
    db.session.commit()
    flash(f'"{addr.label}" 已设为默认地址', 'success')
    return redirect(url_for('user.addresses'))
