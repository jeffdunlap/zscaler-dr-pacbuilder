function FindProxyForURL(url, host) {
    // Zscaler ZIA Disaster Recovery - Custom PAC File
    // Works in conjunction with Zscaler's Pre-Selected Destinations list.
    // Domains listed here will be allowed DIRECT internet access during DR mode.

    host = host.toLowerCase();

    // Custom allowed domains (apex + all subdomains)
    var allowed = [
      whatismyip.com
    ];

    for (var i = 0; i < allowed.length; i++) {
        if (host === allowed[i] || dnsDomainIs(host, "." + allowed[i])) {
            return "DIRECT";
        }
    }

    // Block everything not matched here or in Zscaler's Pre-Selected Destinations
    return "PROXY 127.0.0.1:1";
}
