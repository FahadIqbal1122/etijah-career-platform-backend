create table if not exists email_templates (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  name text not null,
  description text,
  is_active boolean not null default true,
  subject_en text not null default '',
  subject_ar text not null default '',
  body_html_en text not null default '',
  body_html_ar text not null default '',
  variables jsonb not null default '[]',
  updated_at timestamptz default now()
);

create index if not exists email_templates_key_idx on email_templates (key);

insert into email_templates (key, name, description, is_active, subject_en, subject_ar, body_html_en, body_html_ar, variables) values
('report_email', 'Career Report Delivery', 'Sent when a user requests their career report by email. The PDF is attached automatically.', true,
 'Your Career Report is Ready', 'تقريرك المهني جاهز',
 '<div style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>Hi {{full_name}},</p><p>Your full career report is ready and attached to this email as a PDF.</p><p style="margin-top: 24px; color: #6b7280; font-size: 13px;">Etijah Career Platform</p></div>',
 '<div dir="rtl" style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>مرحباً {{full_name}}،</p><p>تقريرك المهني الكامل جاهز الآن ومرفق بهذه الرسالة بصيغة PDF.</p><p style="margin-top: 24px; color: #6b7280; font-size: 13px;">Etijah Career Platform</p></div>',
 '["full_name"]'::jsonb
),
('welcome_email', 'Welcome Email', 'Not wired to a trigger yet — placeholder for a future signup welcome email.', false,
 'Welcome to Etijah Career Platform', 'مرحباً بك في منصة اتجاهي المهنية',
 '<div style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>Hi {{full_name}},</p><p>Welcome aboard!</p></div>',
 '<div dir="rtl" style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>مرحباً {{full_name}}،</p><p>يسعدنا انضمامك إلينا!</p></div>',
 '["full_name"]'::jsonb
),
('waitlist_confirmation', 'Waitlist Confirmation', 'Not wired to a trigger yet — placeholder for a future waitlist signup confirmation.', false,
 'You are on the waitlist', 'تم تسجيلك في قائمة الانتظار',
 '<div style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>Hi {{full_name}},</p><p>Thanks for joining the waitlist — we will be in touch soon.</p></div>',
 '<div dir="rtl" style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>مرحباً {{full_name}}،</p><p>شكراً لانضمامك لقائمة الانتظار، سنتواصل معك قريباً.</p></div>',
 '["full_name"]'::jsonb
),
('feedback_request', 'Post-Assessment Feedback Request', 'Sent automatically after a user completes an assessment, inviting them to fill out the feedback form.', true,
 'How was your assessment experience?', 'كيف كانت تجربتك مع التقييم؟',
 '<div style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>Hi {{full_name}},</p><p>Thanks for completing your career assessment! We would love to hear your feedback — it takes less than 2 minutes and helps us improve.</p><p style="margin: 24px 0;"><a href="{{feedback_url}}" style="background:#7c3aed;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">Share Your Feedback</a></p><p style="margin-top: 24px; color: #6b7280; font-size: 13px;">Etijah Career Platform</p></div>',
 '<div dir="rtl" style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>مرحباً {{full_name}}،</p><p>شكراً لإكمال تقييمك المهني! يسعدنا معرفة رأيك — يستغرق الأمر أقل من دقيقتين ويساعدنا على التحسين.</p><p style="margin: 24px 0;"><a href="{{feedback_url}}" style="background:#7c3aed;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">شاركنا رأيك</a></p><p style="margin-top: 24px; color: #6b7280; font-size: 13px;">منصة اتجاهي المهنية</p></div>',
 '["full_name", "feedback_url"]'::jsonb
),
('results_ready', 'Assessment Results Ready', 'Sent automatically right after a user completes an assessment, linking back to their results page.', true,
 'Your career assessment results are ready', 'نتائج تقييمك المهني جاهزة',
 '<div style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>Hi {{full_name}},</p><p>Your career assessment results are ready to view. Click below to see your personality profile, top strengths, and matched career paths.</p><p style="margin: 24px 0;"><a href="{{results_url}}" style="background:#7c3aed;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">View Your Results</a></p><p style="margin-top: 24px; color: #6b7280; font-size: 13px;">Etijah Career Platform</p></div>',
 '<div dir="rtl" style="font-family: Arial, sans-serif; font-size: 15px; color: #1f2937; line-height: 1.6;"><p>مرحباً {{full_name}}،</p><p>نتائج تقييمك المهني جاهزة الآن للاطلاع عليها. اضغط أدناه لمشاهدة ملفك الشخصي وأبرز نقاط قوتك والمسارات المهنية المناسبة لك.</p><p style="margin: 24px 0;"><a href="{{results_url}}" style="background:#7c3aed;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">شاهد نتائجك</a></p><p style="margin-top: 24px; color: #6b7280; font-size: 13px;">منصة اتجاهي المهنية</p></div>',
 '["full_name", "results_url"]'::jsonb
)
on conflict (key) do nothing;
