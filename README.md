# AlgoCitizens

AlgoCitizens is a participatory budgeting platform for citizens to submit, discuss and vote for local initiatives.

# Important Links

Smart contract deployed on the testnet:
 - address [NAZLP5NI5FU5WJBT32R75VWPSD2UPDBII7C6GGCQA6BF7R6KHEDAYX3RXI](https://testnet.algoexplorer.io/address/NAZLP5NI5FU5WJBT32R75VWPSD2UPDBII7C6GGCQA6BF7R6KHEDAYX3RXI)
 - app ID [479755206](https://testnet.algoexplorer.io/application/479755206)

# Description
## 1. Problem:

There is a great tool in modern democracy such as a participatory budgeting. It is a form of citizen participation in which citizens are involved in the process of deciding how public money is spent. For example, only the NY City participatory budgeting is ~ $40 mln ($1 mln per district). And ppl can submit their idea and decide on how this money should be spent. However, there are some issues that make this process complex, unclear and not that transparent.
![Problems and sulutions](https://cdn.dorahacks.io/static/files/18bcfce98c08a33eb41bd44403092d36.png)


## 2. Solution:

We designed AlgoCitizines, a platform that helps citizens to submit, discuss and vote (or delegate) for initiatives of participatory budgeting and get their proposals self-executed and funded. Also, users can earn city tokens based on their activities (proposals, discussions, votes) which they can exchange on city products and services.


## 3. Key features:

**Token-gated access:** only user with Residence Permit Token (RPT) will be able to submit/vote at the platform. *Disabled on testnet.*

**Submit and discuss proposals.** Once user created their proposal they should sign tx to "submit" it on Algorand blockchain and then discuss it before voting epoch will be started.

**Each user will get limited #of votes per Epoch** (voting period in participatory budgeting, ~2 months), so that they can choose most relevant for their district proposals.

**User has voting power.** It works as a multiplier and increased through: voting (winner proposal); submitting proposal (winner proposal); meaningful discussion (appreciated by community).

**User can delegate their votes(10 out of 10).** Receiver will get entrusted_vote_power, and can use only one delegated vote for each proposal. Also, we added in the smart contract possibility to withdraw your delegation.

**User receives proof-of-voting badge (NFT)**, with clawback fx to prevent malicious behavior. *WIP.*

**Killer feature: Exchange city tokens on a city transport card.** Based on users activities and contribution, they will get city tokens which they can exchange on city products and services. *WIP.*

![Perks](https://cdn.dorahacks.io/static/files/18bcff0e91b7abd35def5cf447a8a3be.png)


## Setup

### Initial setup

1. Clone this repository locally.
2. Install pre-requisites:
   - Make sure to have [Docker](https://www.docker.com/) installed and running on your machine.
   - Install `AlgoKit` - [Link](https://github.com/algorandfoundation/algokit-cli#install): The minimum required version is `1.3.0`. Ensure you can execute `algokit --version` and get `1.3.0` or later.
   - Bootstrap your local environment; run `algokit bootstrap all` within this folder, which will install Poetry, run `npm install` and `poetry install` in the root directory to install NPM and Python packages respectively, set up a `.venv` folder with a Python virtual environment and also install all Python dependencies.
     - For TypeScript projects, it will also run `npm install` to install NPM packages.
     - For all projects, it will copy `.env.template` to `.env`.
   - Run `algokit localnet start` to start a local Algorand network in Docker. If you are using VS Code launch configurations provided by the template, this will be done automatically for you.
3. Open the project and start debugging / developing on:
   - [Backend](backend/README.md) - Refer to the README for more information on how to work with smart contracts.
   - [Frontend](frontend/README.md) - Refer to the README for more information on how to work with the frontend application.


### Subsequently

1. If you update to the latest source code and there are new dependencies, you will need to run `algokit bootstrap all` again.
2. Follow step 3 above.

### Continuous Integration / Continuous Deployment (CI/CD)

This project uses [GitHub Actions](https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions) to define CI/CD workflows, which are located in the [`.github/workflows`](./.github/workflows) folder. You can configure these actions to suit your project's needs, including CI checks, audits, linting, type checking, testing, and deployments to TestNet.

For pushes to `main` branch, after the above checks pass, the following deployment actions are performed:
  - The smart contract(s) are deployed to TestNet using [AlgoNode](https://algonode.io).
  - The frontend application is deployed to a provider of your choice (Netlify, Vercel, etc.). See [frontend README](frontend/README.md) for more information.

> Please note deployment of smart contracts is done via `algokit deploy` command which can be invoked both via CI as seen on this project, or locally. For more information on how to use `algokit deploy` please see [AlgoKit documentation](https://github.com/algorandfoundation/algokit-cli/blob/main/docs/features/deploy.md).

## Tools

This project makes use of Python and React to build Algorand smart contracts and to provide a base project configuration to develop frontends for your Algorand dApps and interactions with smart contracts. The following tools are in use:

- Algorand, AlgoKit, and AlgoKit Utils
- Python dependencies including Poetry, Black, Ruff or Flake8, mypy, pytest, and pip-audit
- React and related dependencies including AlgoKit Utils, Tailwind CSS, daisyUI, use-wallet, npm, jest, playwright, Prettier, ESLint, and Github Actions workflows for build validation

### VS Code

It has also been configured to have a productive dev experience out of the box in [VS Code](https://code.visualstudio.com/), see the [backend .vscode](./backend/.vscode) and [frontend .vscode](./frontend/.vscode) folders for more details.

## Integrating with smart contracts and application clients

Refer to the [backend](backend/README.md) folder for overview of working with smart contracts, [frontend](frontend/README.md) for overview of the React project and the [frontend/contracts](frontend/src/contracts/README.md) folder for README on adding new smart contracts from backend as application clients on your frontend. The templates provided in these folders will help you get started.
When you compile and generate smart contract artifacts, your frontend component will automatically generate typescript application clients from smart contract artifacts and move them to `frontend/src/contracts` folder, see [`generate:app-clients` in package.json](frontend/package.json). Afterwards, you are free to import and use them in your frontend application.

The frontend starter also provides an example of interactions with your AlgoCitizensClient in [`AppCalls.tsx`](frontend/src/components/AppCalls.tsx) component by default.

## Next Steps

You can take this project and customize it to build your own decentralized applications on Algorand. Make sure to understand how to use AlgoKit and how to write smart contracts for Algorand before you start.
