// Path: scripts/database/ensure_user_profile_fields.js
// Run:
//   mongosh "mongodb://USER:PASS@host:27017/lucid?authSource=admin" scripts/database/ensure_user_profile_fields.js
//   docker exec -i lucid-mongodb mongosh lucid < scripts/database/ensure_user_profile_fields.js
//
// Ensures `users` documents have fields aligned with common/contact_profile_env.py.
// Does not store secret values — only contact_profile_key, metadata mirror, and lucid_env scope.

/* global db, print */

db = db.getSiblingDB("lucid");
const COLL = "users";

const DEFAULT_LUCID_ENV = {
  node_operational_config_path: "/app/config/operational-config.json",
  variable_groups: {
    mongodb: true,
    redis: true,
    elasticsearch: true,
    tor: true,
    tron: false,
    blockchain: false,
    payment: false,
    rdp: false,
    session: false,
    api_gateway: true,
    signing: false,
  },
};

function deepMergeMissing(existing, defaults) {
  const base =
    existing !== null && typeof existing === "object" && !Array.isArray(existing) ? { ...existing } : {};
  for (const k of Object.keys(defaults)) {
    const dv = defaults[k];
    if (base[k] === undefined) {
      base[k] = dv;
    } else if (
      dv !== null &&
      typeof dv === "object" &&
      !Array.isArray(dv) &&
      base[k] !== null &&
      typeof base[k] === "object" &&
      !Array.isArray(base[k])
    ) {
      base[k] = deepMergeMissing(base[k], dv);
    }
  }
  return base;
}

print("=== ensure_user_profile_fields: collection=" + COLL + " ===");

let n = 0;
db.getCollection(COLL)
  .find({})
  .forEach((doc) => {
    const profile =
      doc.profile !== null && typeof doc.profile === "object" ? { ...doc.profile } : {};
    if (!profile.metadata || typeof profile.metadata !== "object") {
      profile.metadata = {};
    }
    if (profile.metadata.contact_profile_key === undefined) {
      profile.metadata.contact_profile_key = null;
    }
    profile.lucid_env = deepMergeMissing(profile.lucid_env, DEFAULT_LUCID_ENV);

    const update = { profile: profile };
    if (doc.contact_profile_key === undefined) {
      update.contact_profile_key = null;
    }

    db.getCollection(COLL).updateOne({ _id: doc._id }, { $set: update });
    n += 1;
  });

print("Processed documents: " + n);
print("Done.");
