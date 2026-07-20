import functools
import json
import os
import shutil
import tempfile

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

import card_module
import database_moudle as db
import excel_module
import face_module
import ocr_module
import time_module
import weight_module
import auto_outbound


app = Flask(__name__)
CORS(app)
db.init_database()


def json_error(message, status=400):
    return jsonify({"error": message}), status


def save_upload(file_storage, suffix=".jpg"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file_storage.save(tmp.name)
        return tmp.name


def _token_from_request():
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.headers.get("X-Auth-Token")


def current_user():
    return db.get_user_by_token(_token_from_request())


def require_auth(roles=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return json_error("未登录或登录已过期", 401)
            if roles and user.get("role") not in roles:
                return json_error("权限不足", 403)
            request.current_user = user
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _actor():
    return getattr(request, "current_user", None) or current_user()


def _person_from_card(card_no):
    if not card_no:
        return None
    verification = db.verify_card(card_no)
    if verification.get("valid"):
        card = verification["card"]
        return {"id": card.get("person_id"), "name": card.get("person_name")}
    return None


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or {}
    required = ["username", "password", "name"]
    if any(not data.get(field) for field in required):
        return json_error("username, password and name are required")
    try:
        user = db.create_user(
            username=data["username"],
            password=data["password"],
            name=data["name"],
            role="operator",
            department=data.get("department"),
            phone=data.get("phone"),
        )
        session = db.create_session(user["id"])
        db.log_action("auth.register", user, "user", user["id"], user["username"])
        return jsonify({"user": user, **session}), 201
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    user = db.authenticate_user(data.get("username", ""), data.get("password", ""))
    if not user:
        return json_error("用户名或密码错误", 401)
    session = db.create_session(user["id"])
    db.log_action("auth.login", user, "user", user["id"], user["username"])
    return jsonify({"user": user, **session})


@app.route("/api/auth/logout", methods=["POST"])
@require_auth()
def auth_logout():
    token = _token_from_request()
    db.delete_session(token)
    return jsonify({"success": True})


@app.route("/api/auth/me", methods=["GET"])
@require_auth()
def auth_me():
    return jsonify(request.current_user)


@app.route("/api/dashboard/summary", methods=["GET"])
@require_auth()
def dashboard_summary():
    return jsonify(db.dashboard_summary())


@app.route("/api/ocr/chemical", methods=["POST"])
@require_auth()
def ocr_chemical():
    if "image" not in request.files:
        return json_error("No image file")

    tmp_path = save_upload(request.files["image"])
    try:
        result = ocr_module.recognize_chemical_label(tmp_path, db.find_chemical_candidates())
        db.log_action("ocr.chemical", _actor(), "chemical", result.get("name"), result.get("raw_text"))
        return jsonify(result)
    except Exception as exc:
        return json_error(str(exc), 500)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route("/api/chemicals", methods=["GET"])
@require_auth()
def get_chemicals():
    keyword = request.args.get("keyword", "")
    hazardous_only = request.args.get("hazardous_only", "false").lower() == "true"
    return jsonify(db.list_chemicals(keyword, hazardous_only=hazardous_only))


@app.route("/api/chemicals/<int:chemical_id>", methods=["GET"])
@require_auth()
def get_chemical(chemical_id):
    chemical = db.get_chemical(chemical_id)
    if not chemical:
        return json_error("chemical not found", 404)
    return jsonify(chemical)


@app.route("/api/chemicals", methods=["POST"])
@require_auth(["admin", "keeper", "safety_manager"])
def create_chemical():
    data = request.get_json(silent=True) or {}
    try:
        chemical = db.upsert_chemical(data)
        db.log_action("chemical.create", _actor(), "chemical", chemical["id"], chemical["name"])
        return jsonify(chemical), 201
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/chemicals/<int:chemical_id>", methods=["PUT"])
@require_auth(["admin", "keeper", "safety_manager"])
def update_chemical(chemical_id):
    data = request.get_json(silent=True) or {}
    data["id"] = chemical_id
    try:
        chemical = db.upsert_chemical(data)
        db.log_action("chemical.update", _actor(), "chemical", chemical_id, chemical["name"])
        return jsonify(chemical)
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/chemicals/<int:chemical_id>", methods=["DELETE"])
@require_auth(["admin", "safety_manager"])
def delete_chemical(chemical_id):
    db.delete_chemical(chemical_id)
    db.log_action("chemical.disable", _actor(), "chemical", chemical_id)
    return jsonify({"success": True})


@app.route("/api/chemicals/export", methods=["GET"])
@require_auth()
def export_chemicals():
    chemicals = db.list_chemicals(request.args.get("keyword", ""))
    file_path = os.path.join(tempfile.gettempdir(), "chemical_list.xlsx")
    try:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Chemicals"
        headers = [
            "id",
            "code",
            "name",
            "alias",
            "cas_no",
            "category",
            "specification",
            "stock",
            "unit",
            "min_stock",
            "hazard",
            "danger_level",
            "control_level",
            "location",
            "project_name",
        ]
        ws.append(headers)
        for item in chemicals:
            ws.append([item.get(header) for header in headers])
        wb.save(file_path)
    except Exception:
        excel_module.save_to_excel(chemicals)
    return send_file(file_path, as_attachment=True, download_name="chemical_list.xlsx")


@app.route("/api/people", methods=["GET"])
@require_auth()
def list_people():
    return jsonify(db.list_people(request.args.get("keyword", "")))


@app.route("/api/people", methods=["POST"])
@require_auth(["admin", "keeper", "safety_manager"])
def create_person():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return json_error("name is required")
    person = db.create_person(
        name=data["name"],
        employee_no=data.get("employee_no"),
        department=data.get("department"),
        phone=data.get("phone"),
        role=data.get("role", "operator"),
        status=data.get("status", "active"),
    )
    db.log_action("person.create", _actor(), "person", person["id"], person["name"])
    return jsonify(person), 201


@app.route("/api/card/ports", methods=["GET"])
@require_auth()
def card_ports():
    return jsonify(card_module.list_reader_ports())


@app.route("/api/card/read", methods=["POST"])
@require_auth()
def card_read():
    data = request.get_json(silent=True) or {}
    try:
        result = card_module.read_card(
            card_no=data.get("card_no"),
            port=data.get("port"),
            baudrate=int(data.get("baudrate", 9600)),
            timeout=float(data.get("timeout", 5)),
        )
        db.log_action("card.read", _actor(), "card", result.get("card_no"), json.dumps(result, ensure_ascii=False))
        return jsonify(result)
    except Exception as exc:
        return json_error(str(exc), 500)


@app.route("/api/card/verify", methods=["POST"])
@require_auth()
def card_verify():
    data = request.get_json(silent=True) or {}
    card_no = card_module.normalize_card_no(data.get("card_no"))
    if not card_no:
        return json_error("card_no is required")
    return jsonify(db.verify_card(card_no))


@app.route("/api/card/register", methods=["POST"])
@require_auth(["admin", "keeper", "safety_manager"])
def card_register():
    data = request.get_json(silent=True) or {}
    card_no = data.get("card_no")
    if not card_no:
        return json_error("card_no is required")
    try:
        card = card_module.register_card(
            card_no=card_no,
            person_id=data.get("person_id"),
            person=data.get("person"),
            card_type=data.get("card_type", "ic"),
            status=data.get("status", "active"),
            remark=data.get("remark"),
        )
        db.log_action("card.register", _actor(), "card", card["card_no"], card.get("person_name"))
        return jsonify(card), 201
    except Exception as exc:
        return json_error(str(exc), 500)


@app.route("/api/card/cards", methods=["GET"])
@require_auth()
def card_list():
    return jsonify(db.list_cards(request.args.get("keyword", "")))


@app.route("/api/inventory/transactions", methods=["GET"])
@require_auth()
def inventory_transactions():
    keyword = request.args.get("keyword", "")
    limit = int(request.args.get("limit", 200))
    return jsonify(db.list_inventory_transactions(keyword, limit=limit))


@app.route("/api/inventory/inbound", methods=["POST"])
@require_auth(["admin", "keeper", "safety_manager"])
def inventory_inbound():
    data = request.get_json(silent=True) or {}
    chemical_id = data.get("chemical_id")
    if not chemical_id and data.get("chemical"):
        chemical = db.upsert_chemical(data["chemical"])
        chemical_id = chemical["id"]
    if not chemical_id:
        return json_error("chemical_id or chemical is required")
    try:
        tx = db.create_inventory_transaction(
            "inbound",
            chemical_id,
            data.get("quantity"),
            applicant=_actor(),
            handler=_actor(),
            project_name=data.get("project_name"),
            purpose=data.get("purpose"),
            remark=data.get("remark"),
        )
        db.log_action("inventory.inbound", _actor(), "transaction", tx["id"], tx["transaction_no"])
        return jsonify({"approval_required": False, "transaction": tx})
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/inventory/outbound", methods=["POST"])
@require_auth()
def inventory_outbound():
    data = request.get_json(silent=True) or {}
    chemical_id = data.get("chemical_id")
    chemical = db.get_chemical(chemical_id) if chemical_id else None
    if not chemical:
        return json_error("chemical not found", 404)
    quantity = float(data.get("quantity") or 0)
    if quantity <= 0:
        return json_error("quantity must be greater than 0")

    applicant = _person_from_card(data.get("card_no")) or _actor()
    role = (_actor() or {}).get("role")
    controlled = db.is_controlled_chemical(chemical)
    needs_approval = controlled and role not in ("admin", "safety_manager") and not data.get("approval_id")

    try:
        if needs_approval:
            approval = db.create_approval_request(
                {
                    "request_type": "outbound",
                    "chemical_id": chemical_id,
                    "quantity": quantity,
                    "applicant_id": applicant.get("id"),
                    "applicant_name": applicant.get("name"),
                    "card_no": data.get("card_no"),
                    "project_name": data.get("project_name"),
                    "purpose": data.get("purpose"),
                    "reason": data.get("reason", "危险化学品出库需审批"),
                }
            )
            db.log_action("approval.create", _actor(), "approval", approval["id"], approval["request_no"])
            return jsonify({"approval_required": True, "approval": approval}), 202

        tx = db.create_inventory_transaction(
            "outbound",
            chemical_id,
            quantity,
            applicant=applicant,
            handler=_actor(),
            card_no=data.get("card_no"),
            project_name=data.get("project_name"),
            purpose=data.get("purpose"),
            remark=data.get("remark"),
            approval_id=data.get("approval_id"),
        )
        db.log_action("inventory.outbound", _actor(), "transaction", tx["id"], tx["transaction_no"])
        return jsonify({"approval_required": False, "transaction": tx})
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/inventory/return", methods=["POST"])
@require_auth()
def inventory_return():
    data = request.get_json(silent=True) or {}
    applicant = _person_from_card(data.get("card_no")) or _actor()
    try:
        tx = db.create_inventory_transaction(
            "return",
            data.get("chemical_id"),
            data.get("quantity"),
            applicant=applicant,
            handler=_actor(),
            card_no=data.get("card_no"),
            project_name=data.get("project_name"),
            purpose=data.get("purpose", "归还"),
            remark=data.get("remark"),
        )
        db.log_action("inventory.return", _actor(), "transaction", tx["id"], tx["transaction_no"])
        return jsonify({"transaction": tx})
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/inventory/adjust", methods=["POST"])
@require_auth(["admin", "keeper", "safety_manager"])
def inventory_adjust():
    data = request.get_json(silent=True) or {}
    try:
        tx = db.create_inventory_transaction(
            "adjust",
            data.get("chemical_id"),
            data.get("quantity"),
            applicant=_actor(),
            handler=_actor(),
            project_name=data.get("project_name"),
            purpose=data.get("purpose", "盘点调整"),
            remark=data.get("remark"),
        )
        db.log_action("inventory.adjust", _actor(), "transaction", tx["id"], tx["transaction_no"])
        return jsonify({"transaction": tx})
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/approvals", methods=["GET"])
@require_auth()
def approvals():
    return jsonify(db.list_approvals(status=request.args.get("status", ""), keyword=request.args.get("keyword", "")))


@app.route("/api/approvals/<int:approval_id>/review", methods=["POST"])
@require_auth(["admin", "safety_manager"])
def approval_review(approval_id):
    data = request.get_json(silent=True) or {}
    approved = data.get("approved") in (True, 1, "1", "true", "approved")
    try:
        result = db.review_approval(approval_id, approved, _actor(), data.get("review_note"))
        db.log_action(
            "approval.approve" if approved else "approval.reject",
            _actor(),
            "approval",
            approval_id,
            data.get("review_note"),
        )
        return jsonify(result)
    except ValueError as exc:
        return json_error(str(exc))


@app.route("/api/hazard/summary", methods=["GET"])
@require_auth()
def hazard_summary():
    return jsonify(db.hazard_summary())


@app.route("/api/audit/logs", methods=["GET"])
@require_auth(["admin", "safety_manager"])
def audit_logs():
    return jsonify(db.list_audit_logs(limit=int(request.args.get("limit", 200))))


@app.route("/api/face/recognize", methods=["POST"])
@require_auth()
def face_recognize():
    if "image" not in request.files:
        return json_error("No image file")

    tmp_path = save_upload(request.files["image"])
    try:
        recognizer = face_module.FaceRecognizer()
        person_key = recognizer.recognize_face(tmp_path)
        if person_key and person_key != "Unknown":
            person = db.get_operator(person_key)
            return jsonify({"name": person["name"] if person else person_key, "person": person, "confidence": 0.8})
        return json_error("Unknown face", 404)
    except Exception as exc:
        return json_error(str(exc), 500)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route("/api/face/register", methods=["POST"])
@require_auth(["admin", "keeper", "safety_manager"])
def face_register():
    name = request.form.get("name")
    employee_no = request.form.get("employee_no") or name
    if not name:
        return json_error("name is required")
    if "image" not in request.files:
        return json_error("No image file")

    person_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "known_faces", employee_no)
    os.makedirs(person_dir, exist_ok=True)
    image_path = os.path.join(person_dir, f"{employee_no}_{time_module.get_current_time().strftime('%Y%m%d_%H%M%S')}.jpg")
    tmp_path = save_upload(request.files["image"])
    try:
        shutil.copy(tmp_path, image_path)
        person = db.create_person(name=name, employee_no=employee_no, face_image_path=image_path)
        try:
            face_module.FaceRecognizer().train()
        except Exception:
            pass
        db.log_action("face.register", _actor(), "person", person["id"], person["name"])
        return jsonify({"success": True, "person": person})
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route("/api/weight/current", methods=["GET"])
@require_auth()
def get_current_weight():
    try:
        port = request.args.get("port", "COM3")
        baudrate = int(request.args.get("baudrate", 9600))
        weight = weight_module.read_weight_from_balance(port=port, baudrate=baudrate)
        return jsonify({"weight": weight})
    except Exception as exc:
        return json_error(str(exc), 500)


@app.route("/api/record/usage", methods=["POST"])
@require_auth()
def save_usage_record():
    data = request.get_json(silent=True) or {}
    data.setdefault("timestamp", time_module.get_current_time().strftime("%Y-%m-%d %H:%M:%S"))
    data["raw_json"] = json.dumps(data, ensure_ascii=False)
    record_id = db.insert_usage_record(data)
    db.log_action("usage.record", _actor(), "usage_record", record_id)
    return jsonify({"success": True, "id": record_id, "record": data})


@app.route("/api/records", methods=["GET"])
@require_auth()
def list_records():
    limit = int(request.args.get("limit", 100))
    return jsonify(db.get_all_measurements(limit=limit))


@app.route("/api/auto/outbound", methods=["POST"])
@require_auth()
def auto_outbound():
    """
    自动领用流程接口
    从串口读取卡片、摄像头拍照、OCR识别、读取重量
    返回所有领用信息供前端确认
    """
    data = request.get_json(silent=True) or {}
    try:
        result = auto_outbound.auto_outbound_workflow(
            card_port=data.get("card_port", "COM3"),
            weight_port=data.get("weight_port", "COM4"),
            camera_id=int(data.get("camera_id", 0)),
            card_baudrate=int(data.get("card_baudrate", 9600)),
            weight_baudrate=int(data.get("weight_baudrate", 9600)),
            timeout=float(data.get("timeout", 10))
        )

        # 记录日志
        if result.get("success"):
            db.log_action(
                "auto_outbound.scan",
                _actor(),
                "card",
                result.get("card_no"),
                json.dumps(result, ensure_ascii=False)
            )

        return jsonify(result)
    except Exception as exc:
        return json_error(str(exc), 500)


@app.route("/api/auto/outbound/confirm", methods=["POST"])
@require_auth()
def auto_outbound_confirm():
    """
    确认自动领用并写入数据库
    """
    data = request.get_json(silent=True) or {}
    auto_result = data.get("auto_result")

    if not auto_result:
        return json_error("auto_result is required")

    try:
        tx = auto_outbound.confirm_auto_outbound(
            user_id=_actor()["id"],
            auto_result=auto_result,
            quantity=data.get("quantity"),
            purpose=data.get("purpose", ""),
            project_name=data.get("project_name", "")
        )

        db.log_action(
            "auto_outbound.confirm",
            _actor(),
            "transaction",
            tx["id"],
            tx["transaction_no"]
        )

        return jsonify({"success": True, "transaction": tx})
    except ValueError as exc:
        return json_error(str(exc))
    except Exception as exc:
        return json_error(str(exc), 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
