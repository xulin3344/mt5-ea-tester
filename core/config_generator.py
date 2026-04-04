import os


def generate_configs(
    ea_source_dir,
    symbol="XAUUSDm",
    period="H1",
    from_date="2025.01.01",
    to_date="2026.03.01",
    deposit=10000,
    leverage=500,
):
    """Generate .ini files for each .ex5 file. Returns list of generated names."""
    ex5_files = sorted(f for f in os.listdir(ea_source_dir) if f.endswith(".ex5"))
    if not ex5_files:
        mq5_files = sorted(f for f in os.listdir(ea_source_dir) if f.endswith(".mq5"))
        ex5_files = [f.replace(".mq5", ".ex5") for f in mq5_files]

    if not ex5_files:
        return []

    generated = []
    for f in ex5_files:
        name = os.path.splitext(f)[0]
        rel_path = f"AI\\ea\\{name}.ex5"
        report_rel_path = f"MQL5\\Experts\\AI\\reports\\{name}.htm"

        ini_content = f"""[Tester]
Expert={rel_path}
Symbol={symbol}
Period={period}
Optimization=0
Model=4
FromDate={from_date}
ToDate={to_date}
ForwardMode=0
Deposit={deposit}
Currency=USD
ProfitInPips=0
Leverage={leverage}
ExecutionMode=61
OptimizationCriterion=0
Report={report_rel_path}
ReplaceReport=1
ShutdownTerminal=0
Visual=1
UseLocal=1
UseCloud=0
UseRemote=0
[TesterInputs]"""

        ini_file = os.path.join(ea_source_dir, f"{name}.ini")
        with open(ini_file, "w", encoding="utf-16-le") as ini:
            ini.write("\ufeff")
            ini.write(ini_content)
        generated.append(name)

    return generated
