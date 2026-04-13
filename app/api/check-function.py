import os
import ast
from pathlib import Path
from typing import Dict, List, Set

class FunctionChecker:
    def __init__(self, base_path: str = "api"):
        self.base_path = Path(base_path)
        self.required_functions = self.get_all_required_functions()
        
    def get_all_required_functions(self) -> Dict[str, List[str]]:
        """Retorna todas as funções necessárias por rota"""
        return {
            "cases": [
                "get_all_cases", "get_case_by_id", "get_case_with_all_relations",
                "get_cases_by_client", "get_cases_by_lawyer", "get_cases_by_status",
                "get_cases_by_court", "get_cases_by_area", "get_cases_by_date_range",
                "get_cases_by_value_range", "get_recent_cases", "get_cases_with_deadlines",
                "get_cases_with_pending_tasks", "get_cases_with_upcoming_hearings",
                "get_cases_with_overdue_tasks", "get_cases_by_distribution_date",
                "search_cases_by_number", "search_cases_by_description",
                "create_case", "create_case_with_client", "create_case_with_parts",
                "bulk_create_cases", "update_case", "update_case_status",
                "update_case_lawyer", "update_case_value", "update_case_court",
                "update_case_number", "delete_case", "archive_case", "restore_case",
                "count_cases_by_status", "count_cases_by_area", "count_cases_by_court",
                "count_cases_by_lawyer", "get_case_distribution_by_month",
                "get_average_case_value", "get_total_case_value", "get_cases_summary",
                "generate_case_report_pdf", "generate_cases_list_report",
                "export_cases_to_csv", "get_case_timeline"
            ],
            "clients": [
                "get_all_clients", "get_client_by_id", "get_client_with_cases",
                "get_clients_filtered", "get_clients_by_estado", "get_clients_by_type",
                "get_recent_clients", "search_clients_by_name", "search_clients_by_document",
                "get_clients_by_date_range", "get_clients_with_active_cases",
                "get_clients_without_cases", "create_client", "bulk_create_clients",
                "update_client", "update_client_status", "delete_client", "archive_client",
                "restore_client", "count_clients_by_type", "count_clients_by_estado",
                "get_clients_summary", "check_client_document_exists",
                "get_client_cases_summary", "get_client_financial_summary",
                "generate_client_report_pdf", "export_clients_to_csv"
            ],
            "tasks": [
                "get_all_tasks", "get_task_by_id", "get_tasks_by_case",
                "get_tasks_by_assigned_to", "get_tasks_by_status",
                "get_tasks_by_date_range", "get_pending_tasks", "get_completed_tasks",
                "get_overdue_tasks", "get_tasks_due_today", "get_tasks_due_this_week",
                "get_tasks_by_priority", "get_my_tasks", "search_tasks",
                "create_task", "create_task_with_reminder", "create_recurring_task",
                "bulk_create_tasks", "update_task", "complete_task", "reopen_task",
                "reassign_task", "postpone_task", "update_task_progress", "delete_task",
                "check_overdue_tasks_and_update", "send_task_reminders",
                "generate_recurring_tasks", "count_tasks_by_status", "count_tasks_by_user",
                "count_tasks_by_case", "get_task_completion_rate",
                "get_average_task_completion_time", "get_tasks_summary"
            ],
            "users": [
                "get_all_users", "get_user_by_id", "get_user_by_email",
                "get_users_by_role", "get_users_by_law_firm", "get_active_users",
                "get_inactive_users", "get_users_by_date_range", "search_users",
                "create_user", "bulk_create_users", "update_user", "update_user_role",
                "update_user_status", "change_password", "reset_password",
                "delete_user", "deactivate_user", "activate_user",
                "count_users_by_role", "count_users_by_status", "get_users_summary",
                "get_user_permissions", "update_user_permissions",
                "get_user_activity_log", "get_user_cases_count", "get_user_tasks_count",
                "get_user_hearings_count", "generate_user_report_pdf"
            ],
            "law_firms": [
                "get_law_firm_by_id", "get_law_firm_by_cnpj", "get_law_firm_by_email",
                "create_law_firm", "update_law_firm", "delete_law_firm",
                "get_law_firm_stats", "get_law_firm_users", "get_law_firm_cases",
                "get_law_firm_clients", "get_law_firm_financial_summary",
                "update_law_firm_settings", "get_law_firm_subscription",
                "update_law_firm_subscription", "get_law_firm_usage_stats",
                "generate_law_firm_report_pdf", "export_law_firm_data"
            ]
        }
    
    def scan_route_file(self, file_path: Path) -> Set[str]:
        """Escaneia um arquivo routes.py e retorna as funções encontradas"""
        functions_found = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                tree = ast.parse(file.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions_found.add(node.name)
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id in ['router', 'routes']:
                                # Encontra funções decoradas com @router
                                pass
        except Exception as e:
            print(f"Erro ao ler {file_path}: {e}")
            
        return functions_found
    
    def check_all_routes(self):
        """Verifica todas as rotas e retorna o status"""
        results = {}
        
        for route_name in self.required_functions.keys():
            route_path = self.base_path / route_name / "routes.py"
            functions_found = set()
            
            if route_path.exists():
                functions_found = self.scan_route_file(route_path)
            
            required = set(self.required_functions[route_name])
            implemented = functions_found.intersection(required)
            missing = required - functions_found
            
            results[route_name] = {
                "total_required": len(required),
                "implemented": len(implemented),
                "missing": len(missing),
                "implemented_list": sorted(list(implemented)),
                "missing_list": sorted(list(missing)),
                "extra_functions": functions_found - required if functions_found else set()
            }
            
        return results
    
    def print_report(self):
        """Imprime um relatório detalhado"""
        results = self.check_all_routes()
        
        print("=" * 100)
        print("RELATÓRIO DE FUNÇÕES POR ROTA")
        print("=" * 100)
        
        total_required = 0
        total_implemented = 0
        
        for route, data in results.items():
            print(f"\n📁 {route.upper()}/routes.py")
            print("-" * 80)
            print(f"✅ Implementadas: {data['implemented']}/{data['total_required']}")
            
            if data['implemented_list']:
                print("   Funções implementadas:")
                for func in data['implemented_list']:
                    print(f"   ✓ {func}")
            
            if data['missing_list']:
                print(f"\n❌ Faltando ({len(data['missing_list'])}):")
                for func in data['missing_list']:
                    print(f"   ✗ {func}")
            
            if data['extra_functions']:
                print(f"\n⚠️ Funções extras encontradas:")
                for func in data['extra_functions']:
                    print(f"   ! {func}")
            
            total_required += data['total_required']
            total_implemented += data['implemented']
            
        print("\n" + "=" * 100)
        print(f"📊 TOTAL GERAL: {total_implemented}/{total_required} funções implementadas")
        print(f"📈 Progresso: {(total_implemented/total_required*100):.1f}%")
        print("=" * 100)

if __name__ == "__main__":
    checker = FunctionChecker("app/api")
    checker.print_report()