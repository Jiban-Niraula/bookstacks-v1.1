from flask import jsonify, request

from app.decorators import permission_required
from app.members import bp
from app.members.services import (
    archive_member, create_member, get_member_or_404, list_members,
    member_with_loans, update_member,
)
from app.members.validators import validate_new_member


@bp.get("")
@permission_required("members:read")
def list_all():
    q = request.args.get("q", "").strip()
    include_archived = request.args.get("includeArchived") == "1"
    members = list_members(q, include_archived)
    return jsonify([m.to_dict() for m in members])


@bp.post("")
@permission_required("members:create")
def add():
    data = request.get_json(silent=True) or {}
    membership_number, full_name = validate_new_member(data)
    member = create_member(membership_number, full_name, data)
    return jsonify(member.to_dict()), 201


@bp.get("/<int:member_id>")
@permission_required("members:read")
def get_one(member_id):
    return jsonify(member_with_loans(member_id))


@bp.put("/<int:member_id>")
@permission_required("members:update")
def update(member_id):
    data = request.get_json(silent=True) or {}
    member = update_member(member_id, data)
    return jsonify(member.to_dict())


@bp.delete("/<int:member_id>")
@permission_required("members:delete")
def remove(member_id):
    get_member_or_404(member_id)
    archived_id = archive_member(member_id)
    return jsonify(archived=archived_id)
