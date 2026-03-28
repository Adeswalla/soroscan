# Webhook Signing and Verification Guide

## Overview

SoroScan signs all webhook payloads using HMAC-SHA256 to ensure authenticity and integrity. Subscribers can verify that webhooks truly originated from SoroScan and haven't been tampered with.

## Signature Format

Each webhook includes an `X-SoroScan-Signature` header with the format:

```
X-SoroScan-Signature: sha256=<hex_encoded_hmac_signature>
```

Example:
```
X-SoroScan-Signature: sha256=abcd1234ef5678...
```

## Verification Process

### Step 1: Extract the Signature

```python
signature_header = request.headers.get('X-SoroScan-Signature')
# Format: "sha256=<hex_signature>"
algorithm, signature = signature_header.split('=', 1)
```

### Step 2: Get Your Signing Key

Your signing key is displayed in the SoroScan admin interface:
1. Navigate to Django Admin → Webhook Subscriptions
2. Click on your webhook
3. View the "Webhook Signing Keys" section
4. Copy the active key (the one with `is_active = True`)

### Step 3: Reconstruct the Payload

The payload must be reconstructed exactly as it was signed:
- Use the raw request body (not parsed JSON)
- Maintain exact formatting and byte order

```python
payload_bytes = request.get_data()  # Raw bytes
```

### Step 4: Compute the Expected Signature

```python
import hmac
import hashlib

def verify_webhook_signature(payload_bytes, signature, secret_key):
    """
    Verify a webhook signature.
    
    Args:
        payload_bytes: Raw request body as bytes
        signature: Hex-encoded signature from X-SoroScan-Signature header
        secret_key: Your webhook signing key (hex-encoded)
        
    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = hmac.new(
        secret_key.encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)
```

### Step 5: Verify the Signature

```python
is_valid = verify_webhook_signature(
    payload_bytes=request.get_data(),
    signature=signature,
    secret_key=your_signing_key,
)

if not is_valid:
    return Response({"error": "Invalid signature"}, status=401)

# Process the webhook
event_data = request.json
```

## Complete Example: Python/Flask

```python
import hmac
import hashlib
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Your webhook signing key from SoroScan admin
WEBHOOK_SIGNING_KEY = "your_hex_encoded_key_here"

def verify_webhook_signature(payload_bytes, signature, secret_key):
    """Verify webhook signature using HMAC-SHA256."""
    expected_signature = hmac.new(
        secret_key.encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Get the signature from headers
    signature_header = request.headers.get('X-SoroScan-Signature', '')
    if not signature_header.startswith('sha256='):
        return jsonify({"error": "Invalid signature format"}), 401
    
    signature = signature_header.split('=', 1)[1]
    
    # Get raw payload
    payload_bytes = request.get_data()
    
    # Verify signature
    if not verify_webhook_signature(payload_bytes, signature, WEBHOOK_SIGNING_KEY):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Parse and process the event
    event_data = json.loads(payload_bytes)
    
    print(f"Received event: {event_data['event_type']}")
    print(f"Contract: {event_data['contract_id']}")
    print(f"Ledger: {event_data['ledger']}")
    
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(port=5000)
```

## Complete Example: Node.js/Express

```javascript
import crypto from 'crypto';
import express from 'express';

const app = express();
app.use(express.raw({ type: 'application/json' }));

// Your webhook signing key from SoroScan admin
const WEBHOOK_SIGNING_KEY = 'your_hex_encoded_key_here';

function verifyWebhookSignature(payloadBytes, signature, secretKey) {
    /**
     * Verify webhook signature using HMAC-SHA256.
     */
    const expectedSignature = crypto
        .createHmac('sha256', secretKey)
        .update(payloadBytes)
        .digest('hex');
    
    // Use constant-time comparison to prevent timing attacks
    return crypto.timingSafeEqual(
        Buffer.from(expectedSignature),
        Buffer.from(signature)
    );
}

app.post('/webhook', (req, res) => {
    // Get the signature from headers
    const signatureHeader = req.headers['x-soroscan-signature'] || '';
    if (!signatureHeader.startsWith('sha256=')) {
        return res.status(401).json({ error: 'Invalid signature format' });
    }
    
    const signature = signatureHeader.split('=')[1];
    
    // Get raw payload
    const payloadBytes = req.body;
    
    // Verify signature
    try {
        if (!verifyWebhookSignature(payloadBytes, signature, WEBHOOK_SIGNING_KEY)) {
            return res.status(401).json({ error: 'Invalid signature' });
        }
    } catch (error) {
        return res.status(401).json({ error: 'Signature verification failed' });
    }
    
    // Parse and process the event
    const eventData = JSON.parse(payloadBytes.toString('utf-8'));
    
    console.log(`Received event: ${eventData.event_type}`);
    console.log(`Contract: ${eventData.contract_id}`);
    console.log(`Ledger: ${eventData.ledger}`);
    
    return res.json({ status: 'ok' });
});

app.listen(5000, () => {
    console.log('Webhook server listening on port 5000');
});
```

## Complete Example: Go

```go
package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "io"
    "log"
    "net/http"
    "strings"
)

// Your webhook signing key from SoroScan admin
const WEBHOOK_SIGNING_KEY = "your_hex_encoded_key_here"

func verifyWebhookSignature(payloadBytes []byte, signature string, secretKey string) bool {
    /**
     * Verify webhook signature using HMAC-SHA256.
     */
    h := hmac.New(sha256.New, []byte(secretKey))
    h.Write(payloadBytes)
    expectedSignature := hex.EncodeToString(h.Sum(nil))
    
    return hmac.Equal([]byte(expectedSignature), []byte(signature))
}

func handleWebhook(w http.ResponseWriter, r *http.Request) {
    // Get the signature from headers
    signatureHeader := r.Header.Get("X-SoroScan-Signature")
    if !strings.HasPrefix(signatureHeader, "sha256=") {
        http.Error(w, "Invalid signature format", http.StatusUnauthorized)
        return
    }
    
    signature := strings.TrimPrefix(signatureHeader, "sha256=")
    
    // Get raw payload
    payloadBytes, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read body", http.StatusBadRequest)
        return
    }
    defer r.Body.Close()
    
    // Verify signature
    if !verifyWebhookSignature(payloadBytes, signature, WEBHOOK_SIGNING_KEY) {
        http.Error(w, "Invalid signature", http.StatusUnauthorized)
        return
    }
    
    // Parse and process the event
    var eventData map[string]interface{}
    if err := json.Unmarshal(payloadBytes, &eventData); err != nil {
        http.Error(w, "Failed to parse JSON", http.StatusBadRequest)
        return
    }
    
    fmt.Printf("Received event: %v\n", eventData["event_type"])
    fmt.Printf("Contract: %v\n", eventData["contract_id"])
    fmt.Printf("Ledger: %v\n", eventData["ledger"])
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func main() {
    http.HandleFunc("/webhook", handleWebhook)
    log.Println("Webhook server listening on :5000")
    log.Fatal(http.ListenAndServe(":5000", nil))
}
```

## Webhook Payload Format

Each webhook contains the following JSON payload:

```json
{
  "contract_id": "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
  "event_type": "transfer",
  "payload": {
    "from": "user1",
    "to": "user2",
    "amount": "1000"
  },
  "ledger": 12345,
  "event_index": 0,
  "tx_hash": "abc123def456..."
}
```

## Key Rotation

SoroScan automatically rotates webhook signing keys. When a key is rotated:

1. A new key is created and marked as active
2. The old key is marked as inactive but retained for 7 days
3. Both old and new keys can verify signatures during the grace period
4. After 7 days, old keys are deleted

### Handling Key Rotation

To handle key rotation gracefully:

```python
def verify_webhook_with_rotation(payload_bytes, signature, current_key, old_key=None):
    """
    Verify webhook signature, trying current key first, then old key.
    """
    # Try current key
    if verify_webhook_signature(payload_bytes, signature, current_key):
        return True
    
    # Try old key (if available)
    if old_key and verify_webhook_signature(payload_bytes, signature, old_key):
        return True
    
    return False
```

## Security Best Practices

1. **Always verify signatures** - Never process webhooks without verifying the signature
2. **Use constant-time comparison** - Use `hmac.compare_digest()` or equivalent to prevent timing attacks
3. **Store keys securely** - Never commit signing keys to version control
4. **Use environment variables** - Store keys in environment variables or secrets management
5. **Rotate keys regularly** - Use the admin interface to rotate keys periodically
6. **Monitor failures** - Log signature verification failures to detect attacks
7. **Use HTTPS** - Always use HTTPS for webhook endpoints

## Troubleshooting

### Signature Verification Fails

1. **Check the raw payload** - Ensure you're using the raw request body, not parsed JSON
2. **Verify the key** - Confirm you're using the correct active signing key
3. **Check byte encoding** - Ensure payload is encoded as UTF-8 bytes
4. **Verify header format** - Ensure signature header starts with `sha256=`

### Key Rotation Issues

1. **Update your key** - When you see rotation notifications, update your stored key
2. **Use grace period** - During the 7-day grace period, both old and new keys work
3. **Check admin interface** - Verify the active key in the SoroScan admin

## API Reference

### Webhook Headers

| Header | Value | Description |
|--------|-------|-------------|
| `X-SoroScan-Signature` | `sha256=<hex>` | HMAC-SHA256 signature of payload |
| `X-SoroScan-Timestamp` | ISO 8601 | When the webhook was sent |
| `Content-Type` | `application/json` | Always JSON |

### Webhook Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `contract_id` | string | Stellar contract ID |
| `event_type` | string | Event type name |
| `payload` | object | Event data (varies by type) |
| `ledger` | integer | Ledger sequence number |
| `event_index` | integer | Event index within ledger |
| `tx_hash` | string | Transaction hash |

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the example code for your language
3. Verify your signing key in the admin interface
4. Check application logs for signature verification errors
