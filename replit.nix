{ pkgs }:

{
  deps = [
    pkgs.python311
    pkgs.python311Packages.flask
    pkgs.python311Packages.gunicorn
    pkgs.python311Packages.gitpython
    pkgs.python311Packages.requests
    pkgs.python311Packages.werkzeug
    pkgs.python311Packages.neo4j
    pkgs.python311Packages.networkx
    pkgs.python311Packages.python-dotenv
    pkgs.python311Packages.pygments
    pkgs.python311Packages.openai
    pkgs.python311Packages.transformers
    pkgs.python311Packages.torch
    pkgs.python311Packages.numpy
    pkgs.python311Packages.scikit-learn
    pkgs.python311Packages.tiktoken
    pkgs.python311Packages.click
    pkgs.python311Packages.rich
    pkgs.python311Packages.tabulate
    pkgs.python311Packages.sentence-transformers
    pkgs.python311Packages.tree-sitter
    pkgs.git
  ];
}