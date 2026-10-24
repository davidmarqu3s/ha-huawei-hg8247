# TLS setup and upgrades

The integration connects over HTTPS. Routers with a certificate trusted by Home Assistant need no extra configuration. For a self-signed or otherwise untrusted certificate, supply its SHA256 fingerprint during setup or under **Configure**.

## Get the certificate fingerprint

From a computer on your trusted home network, replace the address below with your router address:

```sh
openssl s_client -connect 192.168.1.1:443 -servername 192.168.1.1 </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256
```

Copy the fingerprint after `sha256 Fingerprint=` into **TLS certificate SHA256 fingerprint**. Colons and spaces are accepted.

This command reads the certificate presented by that address; it does not independently authenticate the router. Enroll the fingerprint only on a trusted network and compare it with the certificate shown in your router administration interface when possible. The integration then checks that exact certificate before sending login credentials.

## Upgrade an existing installation

Existing installations that used HTTP now require HTTPS. If your router uses an untrusted certificate, open the integration's **Configure** dialog and enter its fingerprint. Device tracking choices remain available even if the integration has not loaded successfully.

A changed certificate causes the connection to fail. Check that you are reaching the intended router, then deliberately replace the fingerprint under **Configure**. Leaving the fingerprint blank uses Home Assistant's normal certificate-authority and hostname validation. HTTP-only routers are unsupported.
