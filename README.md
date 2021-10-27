Peerix
======

Peerix is a peer-to-peer binary cache for nix derivations.
Every participating node can pull derivations from each other instances' respective nix-stores.

How does it work?
-----------------

Peerix implements a nix binary cache. When the nix package manager queries peerix, peerix
will ask the network if any other peerix instances hold the package, and if some other instance
holds the derivation, it will download the derivation from that instance.

Installation
------------
There is a nix-module located at `module.nix` that configures your nixos-installation
to automatically use peernix.

These Options exist:

| Option                           | Description                                                                                  |
|----------------------------------|----------------------------------------------------------------------------------------------|
| `services.peerix.enable`         | Enables Peerix                                                                               |
| `services.peerix.openFirewall`   | Open the neccessary firewall ports.                                                          |
| `services.peerix.user`           | What user should the peerix service run under.                                               |
| `services.peerix.group`          | What group should the peerix service run under.                                              |
| `services.peerix.privateKeyFile` | A path to the file that contains the path to the private key to sign your derivations.       |
| `services.peerix.publicKeyFile`  | A path to the file that contains the path to the public key so nix can verify the signature. |
| `services.peerix.publicKey`      | Directly specifiy a public key for the binary caches.                                        |

To sign the peerix cache, you can use `nix-store --generate-binary-cache-key` to create keys to verify authenticity of
the packages in each nix-store.
