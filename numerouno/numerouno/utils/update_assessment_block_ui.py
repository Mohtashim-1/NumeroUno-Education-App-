"""
Update Assessment Quick Links Custom Block with improved UI
"""
import frappe

def update_assessment_block_ui():
    """Update the Custom HTML Block with better UI design"""
    
    block_name = "Assessment Quick Links"
    if not frappe.db.exists("Custom HTML Block", block_name):
        print(f"Custom HTML Block '{block_name}' not found!")
        return
    
    custom_block = frappe.get_doc("Custom HTML Block", block_name)
    
    # Modern, beautiful HTML design
    custom_block.html = """
<div class="assessment-quick-links-modern" style="padding: 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15); margin: 0;">
    <div style="text-align: center; margin-bottom: 32px;">
        <div style="font-size: 48px; margin-bottom: 12px;">🎓</div>
        <h3 style="color: #ffffff; font-size: 32px; font-weight: 700; margin: 0; text-shadow: 0 2px 8px rgba(0,0,0,0.2); letter-spacing: -0.5px;">
            Assessment Dashboard
        </h3>
        <p style="color: rgba(255,255,255,0.95); font-size: 16px; margin-top: 8px; font-weight: 400;">Quick access to all assessment management tools</p>
    </div>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px;">
        <!-- Quiz Activity -->
        <a href="/app/quiz-activity" 
           class="quick-link-card" 
           style="display: block; padding: 28px; background: #ffffff; border-radius: 16px; text-decoration: none; color: #1f2937; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 5px solid #3b82f6; position: relative; overflow: hidden;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05)); border-radius: 50%;"></div>
            <div style="display: flex; align-items: flex-start; position: relative; z-index: 1;">
                <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #3b82f6, #2563eb); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 28px; margin-right: 16px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); flex-shrink: 0;">
                    📝
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 18px; color: #1f2937; margin-bottom: 4px; line-height: 1.3;">Quiz Activity</div>
                    <div style="font-size: 13px; color: #6b7280; line-height: 1.4;">View and manage quiz submissions</div>
                </div>
            </div>
        </a>
        
        <!-- Assessment Plan -->
        <a href="/app/assessment-plan" 
           class="quick-link-card" 
           style="display: block; padding: 28px; background: #ffffff; border-radius: 16px; text-decoration: none; color: #1f2937; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 5px solid #f59e0b; position: relative; overflow: hidden;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05)); border-radius: 50%;"></div>
            <div style="display: flex; align-items: flex-start; position: relative; z-index: 1;">
                <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #f59e0b, #d97706); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 28px; margin-right: 16px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3); flex-shrink: 0;">
                    📋
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 18px; color: #1f2937; margin-bottom: 4px; line-height: 1.3;">Assessment Plan</div>
                    <div style="font-size: 13px; color: #6b7280; line-height: 1.4;">Create and manage plans</div>
                </div>
            </div>
        </a>
        
        <!-- Assessment Result -->
        <a href="/app/assessment-result" 
           class="quick-link-card" 
           style="display: block; padding: 28px; background: #ffffff; border-radius: 16px; text-decoration: none; color: #1f2937; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 5px solid #10b981; position: relative; overflow: hidden;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.05)); border-radius: 50%;"></div>
            <div style="display: flex; align-items: flex-start; position: relative; z-index: 1;">
                <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #10b981, #059669); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 28px; margin-right: 16px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); flex-shrink: 0;">
                    ✅
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 18px; color: #1f2937; margin-bottom: 4px; line-height: 1.3;">Assessment Result</div>
                    <div style="font-size: 13px; color: #6b7280; line-height: 1.4;">View student results</div>
                </div>
            </div>
        </a>
        
        <!-- Student Group -->
        <a href="/app/student-group" 
           class="quick-link-card" 
           style="display: block; padding: 28px; background: #ffffff; border-radius: 16px; text-decoration: none; color: #1f2937; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 5px solid #6366f1; position: relative; overflow: hidden;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(79, 70, 229, 0.05)); border-radius: 50%;"></div>
            <div style="display: flex; align-items: flex-start; position: relative; z-index: 1;">
                <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #6366f1, #4f46e5); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 28px; margin-right: 16px; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); flex-shrink: 0;">
                    👥
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 18px; color: #1f2937; margin-bottom: 4px; line-height: 1.3;">Student Group</div>
                    <div style="font-size: 13px; color: #6b7280; line-height: 1.4;">Manage student groups</div>
                </div>
            </div>
        </a>
        
        <!-- Public Quiz -->
        <a href="/public_quiz_3" 
           target="_blank"
           class="quick-link-card" 
           style="display: block; padding: 28px; background: #ffffff; border-radius: 16px; text-decoration: none; color: #1f2937; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 5px solid #ec4899; position: relative; overflow: hidden;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: linear-gradient(135deg, rgba(236, 72, 153, 0.1), rgba(219, 39, 119, 0.05)); border-radius: 50%;"></div>
            <div style="display: flex; align-items: flex-start; position: relative; z-index: 1;">
                <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #ec4899, #db2777); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 28px; margin-right: 16px; box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3); flex-shrink: 0;">
                    🎯
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 18px; color: #1f2937; margin-bottom: 4px; line-height: 1.3;">Public Quiz</div>
                    <div style="font-size: 13px; color: #6b7280; line-height: 1.4;">Take quiz online</div>
                </div>
                <div style="font-size: 18px; color: #ec4899; font-weight: 700; margin-left: 8px; flex-shrink: 0;">↗</div>
            </div>
        </a>
    </div>
</div>
"""
    
    # Enhanced CSS with smooth animations and modern effects
    custom_block.style = """
.assessment-quick-links-modern {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.assessment-quick-links-modern .quick-link-card {
    position: relative;
    overflow: hidden;
    cursor: pointer;
}

.assessment-quick-links-modern .quick-link-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    transition: left 0.5s ease;
}

.assessment-quick-links-modern .quick-link-card:hover::after {
    left: 100%;
}

.assessment-quick-links-modern .quick-link-card:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.assessment-quick-links-modern .quick-link-card:active {
    transform: translateY(-3px) scale(1.01);
}

/* Icon animation on hover */
.assessment-quick-links-modern .quick-link-card:hover > div > div:first-child > div:first-child {
    transform: scale(1.15) rotate(8deg);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Text color change on hover */
.assessment-quick-links-modern .quick-link-card:hover > div > div:last-child > div:first-child {
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    transition: all 0.3s ease;
}

/* Responsive design */
@media (max-width: 768px) {
    .assessment-quick-links-modern {
        padding: 20px !important;
    }
    
    .assessment-quick-links-modern > div:last-child {
        grid-template-columns: 1fr !important;
        gap: 16px !important;
    }
}
"""
    
    custom_block.save(ignore_permissions=True)
    frappe.db.commit()
    
    print("✅ Custom HTML Block UI updated successfully!")
    print("   - Modern gradient header")
    print("   - Beautiful card design with shadows")
    print("   - Smooth hover animations")
    print("   - Responsive grid layout")
    print("   - Enhanced visual effects")
    
    return {
        "status": "success",
        "message": "UI updated successfully"
    }

