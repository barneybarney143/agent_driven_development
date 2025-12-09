# Chapter 5.0 - Security and Auditing Best Practices

In NetDevOps, where infrastructure is managed as code, the security and audibility of that code are paramount. Handling sensitive information and ensuring code quality are non-negotiable requirements to prevent breaches, misconfigurations, and operational failures. This chapter outlines the essential practices for secrets management and automated code quality auditing.

## Secrets Management

Sensitive information, such as network device credentials (usernames, passwords, API tokens), SSH keys, or cloud provider API keys, must never be stored in plain text within a Git repository. Exposing such secrets is a critical security vulnerability. The workbook mandates a multi-layered approach to secrets management.

### Ansible Vault for Encrypting In-Repository Secrets

The default standard for encrypting variables and files directly within the Git repository is **Ansible Vault**. Ansible Vault uses strong encryption (AES256) to protect sensitive data, allowing it to be safely committed to version control while remaining accessible to Ansible during execution.

#### Encrypting Variables and Files:

1.  **Encrypting a single variable:**
    ```bash
    ansible-vault encrypt_string 'MySecretPassword123!' --name 'device_password'
    # Output will be a YAML-formatted encrypted string you can paste into a vars file:
    # device_password: !vault |
    #    $ANSIBLE_VAULT;1.1;AES256
    #    6230303837653664303330383637313032393233393933393437343132383262333036303233343936393938
    #    ... (truncated for brevity)
    ```
    This encrypted string can then be placed in `group_vars/all/vault.yml` or `host_vars/device_A/vault.yml`.

2.  **Encrypting an entire file:**
    ```bash
    ansible-vault encrypt group_vars/all/secrets.yml
    ```
    This command will prompt for a vault password and encrypt the entire `secrets.yml` file. The file content will become unreadable without the password.

3.  **Creating a new encrypted file:**
    ```bash
    ansible-vault create group_vars/all/new_secrets.yml
    ```
    This opens an editor to create a new file, which will be encrypted upon saving.

#### Decrypting and Managing Vaulted Content:

*   **Viewing an encrypted file:**
    ```bash
    ansible-vault view group_vars/all/secrets.yml
    ```
*   **Editing an encrypted file:**
    ```bash
    ansible-vault edit group_vars/all/secrets.yml
    ```
*   **Changing the vault password:**
    ```bash
    ansible-vault rekey group_vars/all/secrets.yml
    ```

#### Providing the Vault Password at Runtime:

During playbook execution, Ansible needs the vault password to decrypt secrets. This can be provided via:
*   **Command line:** `ansible-playbook my_playbook.yml --ask-vault-pass`
*   **Environment variable:** `ANSIBLE_VAULT_PASSWORD_FILE=/path/to/vault_pass.txt ansible-playbook my_playbook.yml`
*   **Vault password file:** `ansible-playbook my_playbook.yml --vault-password-file /path/to/vault_pass.txt`

For CI/CD pipelines, using a vault password file (whose content is itself a secret managed by the CI/CD system, e.g., GitHub Secrets) or passing the password via an environment variable is the standard practice.

### Leveraging External Secrets Management Systems

For large organizations with mature security infrastructure, integrating with external secrets management systems like **HashiCorp Vault**, **AWS Secrets Manager**, or **Azure Key Vault** is often preferred. These systems offer centralized secret storage, fine-grained access control, auditing, and secret rotation capabilities that go beyond what Ansible Vault provides.

Integration is typically achieved using **Ansible lookup plugins** or custom modules. For example, to retrieve a secret from HashiCorp Vault:

```yaml
- name: Retrieve device credentials from HashiCorp Vault
  ansible.builtin.set_fact:
    device_username: "{{ lookup('community.hashi_vault.vault', 'secret=kv/data/network/device_A:username') }}"
    device_password: "{{ lookup('community.hashi_vault.vault', 'secret=kv/data/network/device_A:password') }}"
  delegate_to: localhost
  run_once: true
```

#### Trade-offs of External Secrets Managers:

While external managers provide robust security governance, it's crucial to address the inherent trade-offs:
*   **Increased Complexity:** Integrating and managing an external secrets system adds another layer of infrastructure and configuration to the automation pipeline.
*   **Dependency on External System:** Playbook runs become dependent on the availability, responsiveness, and correct configuration of the external secrets manager. If the secrets manager is down or inaccessible, automation jobs will fail.
*   **Network Latency:** Retrieving secrets from an external system over the network can introduce minor latency to playbook execution.

The choice between Ansible Vault and an external system depends on organizational security requirements, existing infrastructure, and the scale of operations. For most initial NetDevOps projects, Ansible Vault provides a secure and manageable solution.

## Code Quality Auditing with `ansible-lint`

Automated code quality and security auditing are essential to maintain a high standard for all committed automation content. The specification mandates the integration of **`ansible-lint`** into the development and CI/CD workflow.

`ansible-lint` is a powerful tool that checks playbooks, roles, and collections for common anti-patterns, potential security issues, and general best practices. It helps enforce a unified coding style, identifies deprecated features, and flags configurations that might lead to unexpected behavior or security vulnerabilities.

### Running `ansible-lint`

To run `ansible-lint` on your project:

```bash
ansible-lint .
```
This command will scan all Ansible content in the current directory and its subdirectories, reporting any violations.

### Customizing `ansible-lint` Behavior

Organizations often have specific standards that go beyond `ansible-lint`'s default community-backed rules. The tool can be customized by creating a `.ansible-lint` configuration file in the root of your repository.

This file allows you to:
*   **Enable/Disable Specific Rules:** Turn off rules that don't apply to your workflow or enable stricter checks.
*   **Exclude Paths:** Ignore specific files or directories from linting.
*   **Define Custom Rules:** Implement organization-specific checks.
*   **Specify Warnings/Errors:** Elevate warnings to errors for critical issues.

Example `.ansible-lint` configuration:

```yaml
# .ansible-lint
exclude_paths:
  - roles/legacy_role/
  - inventory/old_hosts.ini
warn_list:
  - no-handler-in-tasks # Warn if handlers are defined directly in tasks, prefer separate handler files
skip_list:
  - no-log-password # Skip warning about logging sensitive data (if handled by external secret manager)
  - command-instead-of-module # Allow 'command' module in specific cases
parse_form_comments: true
```

Enforcing code quality through automated linting ensures that all committed automation content adheres to a unified style, follows best practices, and avoids known issues. This significantly simplifies peer review, reduces the cognitive load for maintainers, and ultimately leads to more reliable and secure network automation deployments. Integrating `ansible-lint` into your CI/CD pipeline (as discussed in Chapter 11.0) makes these checks mandatory before any code can be merged.