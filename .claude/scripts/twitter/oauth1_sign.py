#!/usr/bin/env python3
"""
OAuth 1.0a signature generator for Twitter API v2
Generates Authorization header for authenticated API calls
"""
import hmac
import hashlib
import base64
import time
import os
import urllib.parse
import sys
import json

def percent_encode(text):
    """OAuth 1.0a specific percent encoding (RFC 3986)"""
    return urllib.parse.quote(str(text), safe='-._~')

def generate_oauth_header(method, url, params, consumer_key, consumer_secret, access_token, access_token_secret):
    """Generate OAuth 1.0a Authorization header"""

    # OAuth parameters
    oauth_params = {
        'oauth_consumer_key': consumer_key,
        'oauth_nonce': percent_encode(base64.b64encode(os.urandom(32)).decode('utf-8')[:32]),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': access_token,
        'oauth_version': '1.0',
    }

    # Combine OAuth params with request params
    all_params = {**oauth_params, **params}

    # 1. Normalize parameters (sort lexicographically)
    sorted_params = sorted(all_params.items(), key=lambda item: (item[0], item[1]))
    normalized_params = '&'.join([f"{percent_encode(k)}={percent_encode(v)}" for k, v in sorted_params])

    # 2. Create Signature Base String
    base_url_parts = urllib.parse.urlparse(url)
    base_url = f"{base_url_parts.scheme}://{base_url_parts.netloc}{base_url_parts.path}"

    signature_base_string = '&'.join([
        percent_encode(method.upper()),
        percent_encode(base_url),
        percent_encode(normalized_params)
    ])

    # 3. Create Signing Key
    signing_key = f"{percent_encode(consumer_secret)}&{percent_encode(access_token_secret)}"

    # 4. Generate Signature (HMAC-SHA1)
    hashed = hmac.new(signing_key.encode('utf-8'), signature_base_string.encode('utf-8'), hashlib.sha1)
    oauth_signature = percent_encode(base64.b64encode(hashed.digest()).decode('utf-8'))

    # 5. Construct Authorization Header
    oauth_header_parts = []
    for k, v in sorted(oauth_params.items()):
        oauth_header_parts.append(f'{percent_encode(k)}="{v}"')
    oauth_header_parts.append(f'oauth_signature="{oauth_signature}"')

    return 'OAuth ' + ', '.join(oauth_header_parts)

if __name__ == "__main__":
    if len(sys.argv) != 8:
        print("Usage: python3 oauth1_sign.py <method> <url> <query_params_json> <consumer_key> <consumer_secret> <access_token> <access_token_secret>", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print('  python3 oauth1_sign.py GET "https://api.twitter.com/2/users/me" \'{"user.fields":"public_metrics"}\' API_KEY API_SECRET TOKEN TOKEN_SECRET', file=sys.stderr)
        sys.exit(1)

    method = sys.argv[1]
    url = sys.argv[2]
    query_params_json = sys.argv[3]
    consumer_key = sys.argv[4]
    consumer_secret = sys.argv[5]
    access_token = sys.argv[6]
    access_token_secret = sys.argv[7]

    # Parse query parameters
    params = {}
    if query_params_json and query_params_json != "{}":
        try:
            params = json.loads(query_params_json)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON for query parameters: {e}", file=sys.stderr)
            sys.exit(1)

    # Generate and output header
    auth_header = generate_oauth_header(method, url, params, consumer_key, consumer_secret, access_token, access_token_secret)
    print(auth_header)
