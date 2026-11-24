# Security

Report a vulnerability privately through GitHub's "Report a vulnerability" button on this repository (Security tab). Please do not open a public issue for it.

In scope: the shadowbank package, its CLI and the example generator.

Things worth a private report:

- An input that makes a reader, the network build or the development model hang or use unbounded memory.
- A CSV or JSON value that ends up executed, or that changes another row's result.
- Output that leaks fields the tool is not meant to print.

Never attach real wires, customer records, case files or account numbers to a report. Reproduce with synthetic data.
