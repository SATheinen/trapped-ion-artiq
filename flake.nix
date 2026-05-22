{
  inputs.artiq.url = "git+https://git.m-labs.hk/M-Labs/artiq.git?ref=release-9";
  inputs.nixpkgs.follows = "artiq/nixpkgs";

  outputs = { self, artiq, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          artiq.packages.${system}.artiq
          (pkgs.python3.withPackages (ps: [
            ps.numpy
            ps.matplotlib
            ps.h5py
            ps.qutip
            ps.scipy
            ps.pyyaml
          ]))
        ];
      };
    };

  nixConfig = {
    extra-trusted-public-keys =
      "nixbld.m-labs.hk-1:5aSRVA5b320xbNvu30tqxVPXpld73bhtOeH6uAjRyHc=";
    extra-substituters = "https://nixbld.m-labs.hk";
  };
}
