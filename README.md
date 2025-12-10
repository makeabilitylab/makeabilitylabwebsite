# Makeability Lab Website

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

The [Makeability Lab](https://makeabilitylab.cs.washington.edu) is an advanced research lab directed by Professor Jon Froehlich in Human-AI in the Allen School of Computer Science at the University of Washington. Founded in 2012 by Froehlich and students, the Makeability Lab specializes in HCI and applied machine learning for high-impact problems in accessibility, computational urban science, and augmented reality.

This repository contains the source code for the lab's website, built using **Django** (backend) and **Bootstrap/JavaScript** (frontend).

## 🚀 Getting Started

We use Docker to containerize our development environment, ensuring consistency across macOS and Windows.

* **New Contributors:** Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed installation instructions, coding standards, and workflow.
* **Deployment:** For information on our server infrastructure and logging, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## 🛠 Tech Stack

* **Backend:** Python / Django
* **Database:** PostgreSQL
* **Frontend:** HTML5, SCSS, Bootstrap, jQuery
* **Infrastructure:** Docker, Docker Compose

## 📂 Project Structure

```
makeabilitylabwebsite/
├── website/          # Main Django application
├── static/           # Static assets (CSS, JS, images)
├── media/            # User-uploaded content (publications, slides)
├── templates/        # Django HTML templates
└── docs/             # Additional documentation
```

## 📄 Documentation

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local development setup, workflow, and pull request guidelines |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production servers, logging, and data management |
| [Troubleshooting Wiki](https://github.com/makeabilitylab/makeabilitylabwebsite/wiki/Troubleshooting) | Common issues and solutions |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and request features.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
