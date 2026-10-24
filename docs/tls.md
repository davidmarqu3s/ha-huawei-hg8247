# HTTPS setup and upgrades

Version 0.2.0 requires HTTPS. For routers with a self-signed or otherwise untrusted certificate, copy the certificate’s SHA256 fingerprint into the integration once. Routers with a certificate trusted by Home Assistant need no fingerprint. HTTP-only routers are unsupported.

## Upgrade from 0.1.x

1. While connected to your trusted home network, get your router’s fingerprint using either method below. You do not need to sign in to the router.
2. Update the integration through HACS and restart Home Assistant.
3. Open **Settings → Devices & services → Huawei HG8247 → Configure**.
4. Paste the fingerprint into **TLS certificate SHA256 fingerprint** and save.

Your tracked-device choices are preserved. The Configure dialog remains available if the integration cannot connect after the update; its entities may be unavailable until the fingerprint is saved.

For a new installation, enter the fingerprint on the initial setup form alongside the router address and login.

## Get the fingerprint in a browser

1. Open your router’s HTTPS address, usually `https://192.168.1.1`. Replace the address if your router uses a different one.
2. Open the browser’s certificate viewer. In Firefox, select **Advanced → View Certificate** on the certificate warning page. In Chrome, open **Not secure → Certificate details** beside the address bar; wording can vary by version.
3. Select the router’s server certificate and copy its **SHA-256 fingerprint**. Use the certificate fingerprint, not a public-key fingerprint or the SHA-1 value.

See the [Firefox certificate-viewer guide](https://support.mozilla.org/en-US/kb/secure-website-certificate) or [Chrome SHA-256 fingerprint instructions](https://support.hpe.com/hpesc/public/docDisplay?docId=sd00004003en_us&docLocale=en_US&page=GUID-F0CCAF44-7B2E-4666-A4DA-25695F23B35F.html) if you cannot find the viewer.

## Get the fingerprint in a terminal

On macOS or Linux with OpenSSL available, replace the address below with your router address:

```sh
openssl s_client -connect 192.168.1.1:443 -servername 192.168.1.1 </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256
```

Copy only the hexadecimal value after `=`. Colons and spaces are accepted in the Home Assistant field.

## Trust and certificate changes

Both methods read the certificate presented by that address; they do not independently authenticate the router. Enroll the fingerprint on a trusted network and compare it with an independently known certificate fingerprint when available. The integration then checks that exact certificate before sending login credentials.

If the certificate changes, the integration stops connecting. Verify the router’s identity before replacing the fingerprint under **Configure**. Leaving the fingerprint blank uses Home Assistant’s normal certificate-authority and hostname validation.
