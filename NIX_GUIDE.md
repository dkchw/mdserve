# Nix & Home Manager Installation Guide for `mdserve`

This repository is equipped with a Nix Flake (`flake.nix`) that makes it easy to run, build, and integrate `mdserve` into your NixOS or Home Manager configuration.

---

## Quick Start (Without Installation)

You can run `mdserve` immediately using `nix run` without installing it system-wide:

```bash
# Run in the current directory on default port (2112)
nix run github:dkchw/mdserve

# Run on a custom port
nix run github:dkchw/mdserve -- 8080

# Run with custom bind address
nix run github:dkchw/mdserve -- 8080 --bind 127.0.0.1
```

*(Replace `github:dkchw/mdserve` with `.` if you are in the local repository directory.)*

---

## 1. Declarative Installation via Home Manager Flake

To integrate `mdserve` into your Home Manager flake setup, follow these steps.

### Step A: Add to `flake.nix` inputs

Add this repository to your flake inputs:

```nix
inputs = {
  # ... your other inputs ...

  mdserve = {
    url = "github:dkchw/mdserve";
    inputs.nixpkgs.follows = "nixpkgs"; # Optional, aligns nixpkgs versions
  };
};
```

---

### Step B: Choose an Installation Method

You can install `mdserve` in one of two ways: **directly as a package** or **using the Home Manager module**.

#### Method 1: Installing the Package directly (Recommended for CLI-only use)

Pass the `mdserve` input into your Home Manager configuration outputs, then add the package to your `home.packages` list:

```nix
{ inputs, pkgs, ... }: {
  home.packages = [
    inputs.mdserve.packages.${pkgs.system}.default
  ];
}
```

#### Method 2: Using the Home Manager Module (Recommended for auto-starting background service)

1. Import the module in your Home Manager configuration:

   ```nix
   { inputs, pkgs, ... }: {
     imports = [
       inputs.mdserve.homeManagerModules.default
     ];

     # Configure and enable the service
     services.mdserve = {
       enable = true;
       port = 2112;              # Port to listen on (default: 2112)
       bind = "127.0.0.1";       # Bind address (default: 127.0.0.1)
       workingDirectory = "/home/yourusername/Documents"; # Optional directory to serve (defaults to home directory)
     };
   }
   ```

2. When using this module on Linux, it will automatically set up and enable a user-level Systemd service (`mdserve.service`).

---

### Step C: Apply Configuration

Rebuild your configuration to apply the changes:

```bash
home-manager switch --flake .#your-username
```
*(Or if using NixOS system-wide home-manager configuration, rebuild your system using `nixos-rebuild switch`)*

---

## 2. Managing the Systemd Service

If you installed using the module (Method 2) with `services.mdserve.enable = true`, you can manage the service using user-level systemctl commands:

```bash
# Check service status
systemctl --user status mdserve

# Restart the service
systemctl --user restart mdserve

# Stop the service
systemctl --user stop mdserve

# View real-time logs
journalctl --user -u mdserve -f
```

---

## 3. Alternative: Installing via Nixpkgs Overlay

If you prefer to overlay `mdserve` onto your system's package set so that it is available via `pkgs.mdserve`, add the overlay to your Nixpkgs configuration:

```nix
{ inputs, ... }: {
  nixpkgs.overlays = [
    inputs.mdserve.overlays.default
  ];

  # Now you can use it anywhere in your configuration as standard pkgs:
  home.packages = [
    pkgs.mdserve
  ];
}
```
