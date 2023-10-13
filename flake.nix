{
  description = "A basic flake with a shell";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.05";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.default = pkgs.mkShell {
        packages = [ 
          pkgs.bashInteractive 
          pkgs.python39 
          pkgs.qt5.qtbase
          pkgs.qt5.full
          pkgs.python39Packages.pyserial
          pkgs.python39Packages.pyqt5 
          pkgs.python39Packages.pyqt5_sip
          pkgs.python39Packages.pynput
          pkgs.python39Packages.python-mpv-jsonipc
        ];
      };
    });
}
