#!/usr/bin/env bash
# PG Connect — read-endpoint smoke test.
# Hits every GET endpoint as the role that owns it and reports status + whether data came back.
#
#   API_BASE=http://127.0.0.1:5000 bash docs/kowshik-dev/scripts/readcheck.sh
#
# Expected on a healthy, seeded instance: 34 reads, all 200, 0 failures.
set -u

API="${API_BASE:-http://127.0.0.1:5000}/api"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
fails=0

login() {
  curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}" | jq -r '.data.access_token // empty'
}

ADM=$(login admin@pgconnect.com        Admin@12345)
OWN=$(login owner.rajesh@pgconnect.com Owner@12345)
MGR=$(login manager.suresh@pgconnect.com Manager@12345)
TEN=$(login tenant.rahul@gmail.com     Tenant@12345)

for pair in "ADM:$ADM" "OWN:$OWN" "MGR:$MGR" "TEN:$TEN"; do
  [ -n "${pair#*:}" ] || { echo "LOGIN FAILED for ${pair%%:*} — check seed data / credentials" >&2; exit 1; }
done

hit() { # $1 role label, $2 token (may be empty), $3 path
  if [ -n "$2" ]; then
    code=$(curl -s -o "$TMP" -w "%{http_code}" "$API$3" -H "Authorization: Bearer $2")
  else
    code=$(curl -s -o "$TMP" -w "%{http_code}" "$API$3")
  fi
  rows=$(jq -r 'if (.data|type)=="array" then (.data|length)
                elif (.data|type)=="object" then ((.data.items // .data.properties // .data.all_items // []) | length)
                elif .data == null then 0 else 1 end' "$TMP" 2>/dev/null)
  err=$(jq -r '.error.code // empty' "$TMP" 2>/dev/null)
  [ "$code" = "200" ] || fails=$((fails+1))
  printf "%-8s %-46s %-4s rows=%-4s %s\n" "$1" "$3" "$code" "${rows:-?}" "$err"
}

echo "=== public ==="
hit public  ""   /health
hit public  ""   "/properties/search?per_page=50"
hit public  ""   /properties/1
hit public  ""   "/properties/compare?ids=1,2"
hit public  ""   /properties/1/reviews
hit public  ""   /maps/markers
hit public  ""   "/maps/nearby?lat=12.93&lng=77.62&radius=20"

echo "=== owner ==="
hit owner   "$OWN" /auth/me
hit owner   "$OWN" /properties/owner/my-properties
hit owner   "$OWN" /bookings/property/1
hit owner   "$OWN" /tenants/property/1
hit owner   "$OWN" /finance/invoices/property/1
hit owner   "$OWN" /finance/expenses/property/1
hit owner   "$OWN" /finance/summary/property/1
hit owner   "$OWN" /complaints/property/1
hit owner   "$OWN" /tenants/visitors/property/1
hit owner   "$OWN" /food/property/1
hit owner   "$OWN" /maps/owner-properties
hit owner   "$OWN" /notifications

echo "=== manager ==="
hit manager "$MGR" /auth/me
hit manager "$MGR" /tenants/property/1
hit manager "$MGR" /bookings/property/1
hit manager "$MGR" /finance/summary/property/1

echo "=== tenant ==="
hit tenant  "$TEN" /auth/me
hit tenant  "$TEN" /bookings/my-bookings
hit tenant  "$TEN" /tenants/my-stay
hit tenant  "$TEN" /finance/invoices/my-invoices
hit tenant  "$TEN" /complaints/my-complaints
hit tenant  "$TEN" /wishlist
hit tenant  "$TEN" /notifications
hit tenant  "$TEN" /food/property/1

echo "=== admin ==="
hit admin   "$ADM" /admin/analytics
hit admin   "$ADM" /admin/users
hit admin   "$ADM" /admin/verifications
hit admin   "$ADM" /admin/audit-logs

echo
echo "failures: $fails"
[ "$fails" -eq 0 ] || exit 1
