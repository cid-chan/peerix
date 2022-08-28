{ lib, config, pkgs, ... }:

with lib;

let
  cfg = config.services.peerix;

  removedUser = "From now on, Peerix will always run under its own user and group. You should remove the user which you have configured yourself.";

in {
  imports = [
    (mkRemovedOptionModule ["services" "peerix" "user"] removedUser)
    (mkRemovedOptionModule ["services" "peerix" "group"] removedUser)
  ];

  options = {
    services.peerix = {
      enable = lib.mkEnableOption "peerix";

      openFirewall = lib.mkOption {
        type = types.bool;
        default = true;
        description = ''
          Defines whether or not firewall ports should be opened for it.
        '';
      };

      privateKeyFile = lib.mkOption {
        type = types.nullOr types.path;
        default = null;
        description = ''
          File containing the private key to sign the derivations with.
        '';
      };

      publicKeyFile = lib.mkOption {
        type = types.nullOr types.path;
        default = null;
        description = ''
          File containing the public key to sign the derivations with.
        '';
      };

      publicKey = lib.mkOption {
        type = types.nullOr types.str;
        default = null;
        description = ''
          The public key to sign the derivations with.
        '';
      };

      globalCacheTTL = lib.mkOption {
        type = types.nullOr types.int;
        default = null;
        description = ''
          How long should nix store narinfo files.

          If not defined, the module will not reconfigure the entry.
          If it is defined, this will define how many seconds a cache entry will
          be stored.

          By default not given, as it affects the UX of the nix installation.
        '';
      };

      package = mkOption {
        type = types.package;
        default = (import ./default.nix).default or pkgs.peerix;
        defaultText = literalExpression "pkgs.peerix";
        description = "The package to use for peerix";
      };
    };
  };

  config = lib.mkIf (cfg.enable) {
    systemd.services.peerix = {
      enable = true;
      description = "Local p2p nix caching daemon";
      wantedBy = ["multi-user.target"];
      serviceConfig = {
        Type = "simple";

        User = "peerix";
        Group = "peerix";

        PrivateMounts = true;
        PrivateDevices = true;
        PrivateTmp = true;
        PrivateIPC = true;
        PrivateUsers = true;

        SystemCallFilters = [
          "@aio"
          "@basic-io"
          "@file-system"
          "@io-event"
          "@process"
          "@network-io"
          "@timer"
          "@signal"
          "@alarm"
        ];
        SystemCallErrorNumber = "EPERM";

        ProtectSystem = "full";
        ProtectHome = true;
        ProtectHostname = true;
        ProtectClock = true;
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectKernelLogs = true;
        ProtectControlGroups = true;
        RestrictNamespaces = "";

        NoNewPrivileges = true;
        ReadOnlyPaths = lib.mkMerge [
          ([
            "/nix/var"
            "/nix/store"
          ])

          (lib.mkIf (cfg.privateKeyFile != null) [
            cfg.privateKeyFile
          ])
        ];
        ExecPaths = [
          "/nix/store"
        ];
        Environment = lib.mkIf (cfg.privateKeyFile != null) [
          "NIX_SECRET_KEY_FILE=${cfg.privateKeyFile}"
        ];
      };
      script = ''
        exec ${cfg.package}/bin/peerix
      '';
    };

    users.users.peerix = {
      description = config.systemd.services.peerix.description;
      isSystemUser = true;
      group = "peerix";
    };
    users.groups.peerix = {};

    nix = {
      settings = {
        substituters = [
          "http://127.0.0.1:12304/"
        ];
        trusted-public-keys = [
          (lib.mkIf (cfg.publicKeyFile != null) (builtins.readFile cfg.publicKeyFile))
          (lib.mkIf (cfg.publicKey != null) cfg.publicKey)
        ];
      };
      extraOptions = lib.mkIf (cfg.globalCacheTTL != null) ''
        narinfo-cache-negative-ttl = ${toString cfg.globalCacheTTL}
        narinfo-cache-positive-ttl = ${toString cfg.globalCacheTTL}
      '';
    };

    networking.firewall = lib.mkIf (cfg.openFirewall) {
      allowedTCPPorts = [ 12304 ];
      allowedUDPPorts = [ 12304 ];
    };
  };
}
