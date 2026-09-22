from flask import Flask, jsonify

app = Flask(__name__)

LEDGER_DATA = {
    "A1123": [{"amount": 340, "timestamp": "10:02am"}, {"amount": 340, "timestamp": "10:03am"}],
    "B2001": [{"amount": 340, "timestamp": "10:02am"}, {"amount": 340, "timestamp": "10:03am"}],
    "B2002": [{"amount": 340, "timestamp": "10:02am"}, {"amount": 340, "timestamp": "10:03am"}]
    }   

REFUND_RECORDS = {
    "A1123": {"refund_count_12mo": 0},        
    "B2001": {"refund_count_12mo": 0},
    "B2002": {"refund_count_12mo": 2}
}

DISPUTE_RECORDS = {
    "A1123": {"open_disputes": [{"merchant": "SameMerchant", "related": False}]},
    "B2001": {"open_disputes": [{"merchant": "SameMerchant", "related": True}]},
    "B2002": {"open_disputes": [{"merchant": "SameMerchant", "related": False}]},
    }

@app.route("/ledger/<order_id>")
def get_ledger(order_id):
 
    if order_id in LEDGER_DATA:
        return jsonify(LEDGER_DATA[order_id])
    else:
        return f"No ledger data found for {order_id}", 404

@app.route("/refund-history/<order_id>")
def get_refund_history(order_id):
    record = REFUND_RECORDS.get(order_id, {"refund_count_12mo": 0})
    isflagged = record["refund_count_12mo"] > 0
    return jsonify({"isflagged": isflagged, "note": f"{record['refund_count_12mo']} refunds in past 12 months"})

@app.route("/dispute-flags/<order_id>")
def get_dispute_flags(order_id):
    record = DISPUTE_RECORDS.get(order_id, {"open_disputes": []})
    related = any(d["related"] for d in record["open_disputes"])
    return jsonify({"isflagged": related, "note": f"{len(record['open_disputes'])} open disputes"})

if __name__ == "__main__":
    app.run(port=8000)