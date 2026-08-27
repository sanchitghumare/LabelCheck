import mongoose from "mongoose";

const ruleCheckSchema = new mongoose.Schema(
  {
    rule_name: {
      type: String,
      required: true,
      trim: true,
    },

    status: {
      type: String,
      enum: ["PASS", "FAIL"],
      required: true,
    },

    details: {
      type: String,
      required: true,
      trim: true,
    },
  },
  { _id: false }
);

const auditSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },

    scan_id: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },

    timestamp: {
      type: Date,
      required: true,
    },

    verdict: {
      type: String,
      enum: ["COMPLIANT", "NON_COMPLIANT"],
      required: true,
    },

    px_per_mm: {
      type: Number,
      required: true,
      min:  0.000001,
    },

    extracted_fields: {
      mrp: Number,

      net_quantity_value: Number,

      net_quantity_unit: String,

      mfg_date: String,

      manufacturer_name: String,

      manufacturer_address: String,

      consumer_care_contact: String,
    },

    rule_checks: {
      type: [ruleCheckSchema],
      default: [],
    },

    extraction_confidence: {
      type: Map,
      of: Number,
      default: {},
    },

    extraction_evidence: {
      type: Map,
      of: mongoose.Schema.Types.Mixed,
      default: {},
    },

    ruleset_version: {
      type: String,
      required: true,
      trim: true,
    },

    calibration_fallback: {
      type: Boolean,
      default: false,
    },

    barcode_data: {
      type: String,
      default: null,
    },
  },
  {
    timestamps: true,
  }
);

// Efficient dashboard query:
// "Give me this user's audits, newest first."
auditSchema.index({
  userId: 1,
  timestamp: -1,
});

const Audit =
  mongoose.models.Audit ||
  mongoose.model("Audit", auditSchema);

export default Audit;