"""
Script to add custom block to Assessment workspace
"""
import frappe
import json

def add_custom_block_to_assessment_workspace():
    """Add custom block with quick links to Assessment workspace"""
    
    # Check if Assessment workspace exists (try both spellings)
    workspace_name = None
    for name in ["Assessment", "Assesment", "assesment"]:
        if frappe.db.exists("Workspace", name):
            workspace_name = name
            break
    
    if not workspace_name:
        print("Assessment workspace not found. Creating new workspace...")
        # Create new Assessment workspace
        workspace = frappe.new_doc("Workspace")
        workspace.name = "Assessment"
        workspace.label = "Assessment"
        workspace.title = "Assessment"
        workspace.icon = "assessment"
        workspace.public = 1
        workspace.content = '[]'
        workspace.insert(ignore_permissions=True)
        workspace_name = "Assessment"
        print(f"Created workspace: {workspace_name}")
    else:
        print(f"Found workspace: {workspace_name}")
    
    # Create or get Custom HTML Block
    block_name = "Assessment Quick Links"
    if not frappe.db.exists("Custom HTML Block", block_name):
        print(f"Creating Custom HTML Block: {block_name}")
        custom_block = frappe.new_doc("Custom HTML Block")
        custom_block.name = block_name
        custom_block.private = 0
        
        # HTML content with links
        custom_block.html = """
<div class="assessment-quick-links" style="padding: 20px;">
    <h4 style="margin-bottom: 20px; color: #1e3a8a; font-weight: 600;">Quick Links</h4>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
        <a href="/app/quiz-activity" 
           class="quick-link-btn" 
           style="display: block; padding: 15px; background: #f0f9ff; border: 2px solid #0ea5e9; border-radius: 8px; text-decoration: none; color: #0c4a6e; transition: all 0.3s;">
            <div style="font-size: 24px; margin-bottom: 8px;">📝</div>
            <div style="font-weight: 600; font-size: 14px;">Quiz Activity</div>
        </a>
        
        <a href="/app/assessment-plan" 
           class="quick-link-btn" 
           style="display: block; padding: 15px; background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; text-decoration: none; color: #78350f; transition: all 0.3s;">
            <div style="font-size: 24px; margin-bottom: 8px;">📋</div>
            <div style="font-weight: 600; font-size: 14px;">Assessment Plan</div>
        </a>
        
        <a href="/app/assessment-result" 
           class="quick-link-btn" 
           style="display: block; padding: 15px; background: #dcfce7; border: 2px solid #10b981; border-radius: 8px; text-decoration: none; color: #065f46; transition: all 0.3s;">
            <div style="font-size: 24px; margin-bottom: 8px;">✅</div>
            <div style="font-weight: 600; font-size: 14px;">Assessment Result</div>
        </a>
        
        <a href="/app/student-group" 
           class="quick-link-btn" 
           style="display: block; padding: 15px; background: #e0e7ff; border: 2px solid #6366f1; border-radius: 8px; text-decoration: none; color: #312e81; transition: all 0.3s;">
            <div style="font-size: 24px; margin-bottom: 8px;">👥</div>
            <div style="font-weight: 600; font-size: 14px;">Student Group</div>
        </a>
        
        <a href="/public_quiz_3" 
           target="_blank"
           class="quick-link-btn" 
           style="display: block; padding: 15px; background: #fce7f3; border: 2px solid #ec4899; border-radius: 8px; text-decoration: none; color: #831843; transition: all 0.3s;">
            <div style="font-size: 24px; margin-bottom: 8px;">🎯</div>
            <div style="font-weight: 600; font-size: 14px;">Public Quiz</div>
            <div style="font-size: 11px; margin-top: 4px; opacity: 0.7;">Opens in new tab</div>
        </a>
    </div>
</div>
"""
        
        # CSS for hover effects
        custom_block.style = """
.assessment-quick-links .quick-link-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
"""
        
        custom_block.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Created Custom HTML Block: {block_name}")
    else:
        print(f"Custom HTML Block already exists: {block_name}")
    
    # Get workspace and add custom block
    workspace = frappe.get_doc("Workspace", workspace_name)
    
    # Check if custom block already exists in workspace
    existing_block = None
    if workspace.custom_blocks:
        for block in workspace.custom_blocks:
            if block.custom_block_name == block_name:
                existing_block = block
                break
    
    if not existing_block:
        # Add custom block to workspace
        workspace.append("custom_blocks", {
            "custom_block_name": block_name,
            "label": "Assessment Quick Links"
        })
        workspace.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Added custom block to workspace: {workspace_name}")
    else:
        print(f"Custom block already exists in workspace")
    
    # Also update workspace content to include the custom block
    try:
        content = json.loads(workspace.content) if workspace.content else []
        
        # Check if custom block is already in content
        block_exists = any(
            item.get("type") == "custom_block" and 
            item.get("data", {}).get("custom_block_name") == block_name
            for item in content
        )
        
        if not block_exists:
            # Add custom block to content at the beginning
            content.insert(0, {
                "type": "custom_block",
                "data": {
                    "custom_block_name": block_name,
                    "col": 12
                }
            })
            workspace.content = json.dumps(content)
            workspace.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"Added custom block to workspace content")
        else:
            print(f"Custom block already in workspace content")
            
    except Exception as e:
        print(f"Error updating workspace content: {str(e)}")
        # Continue anyway - the custom block is added via the table
    
    print(f"\n✅ Success! Custom block added to Assessment workspace")
    print(f"   Workspace: {workspace_name}")
    print(f"   Custom Block: {block_name}")
    print(f"   Access at: /app/{workspace_name.lower()}")
    
    return {
        "status": "success",
        "workspace": workspace_name,
        "custom_block": block_name
    }

