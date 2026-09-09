insert into email_templates (key, name, description, is_active, subject_en, subject_ar, body_html_en, body_html_ar, variables) values
('beta_assessment_reminder', 'Beta Reminder — Assessment Not Started', 'Reminder email for people who signed up for the private beta but have not yet completed the assessment ("your place is still reserved"). Both languages are in a single email body (like beta_invite/ai_impact_ready), so body_html_en and body_html_ar are identical. Not yet wired to any automatic trigger — send manually until a "signed up but incomplete" job is built.', true,
$subj$Your place in Etijahi is still reserved$subj$,
$subj$مقعدك في إتجاهي ما زال محجوزاً$subj$,
$body$<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<!-- ============================================================
     ETIJAHI — Beta reminder ("your place is still reserved")
     SUBJECT (AR): مقعدك في إتجاهي ما زال محجوزاً
     SUBJECT (EN): Your place in Etijahi is still reserved
     Access links: AR https://myetijahi.com/ar/assessment
                   EN https://myetijahi.com/en/assessment
     Palette: #0052CC blue · #00C9A7 teal · #EBF3FF light ·
              #2D2D2D charcoal · #FFFFFF white.
     ============================================================ -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<title>Etijahi · مقعدك ما زال محجوزاً</title>
<style>
  body, table, td { -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }
  img { border:0; outline:none; text-decoration:none; -ms-interpolation-mode:bicubic; }
  a { text-decoration:none; }
  @media only screen and (max-width:620px) {
    .px       { padding-left:22px !important; padding-right:22px !important; }
    .hero     { padding-top:30px !important; padding-bottom:22px !important; }
    .logo     { width:240px !important; max-width:70% !important; }
    .cta a    { display:block !important; padding-left:20px !important; padding-right:20px !important; }
    .eyebrow td { font-size:11px !important; letter-spacing:0.5px !important; }
    .callout  { padding:16px 16px !important; }
    .accesscard { padding:22px 18px !important; }
    .herotitle { font-size:26px !important; }
    .support-col { display:block !important; width:100% !important; padding:0 0 14px 0 !important; }
  }
</style>
</head>
<body style="margin:0; padding:0; background:#EBF3FF;">
<span style="display:none; font-size:0; line-height:0; max-height:0; opacity:0; overflow:hidden; mso-hide:all;">خمس عشرة دقيقة فقط، واختبار الـBeta سيُغلق قريباً · Just fifteen minutes — the beta closes soon.</span>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#EBF3FF; margin:0; padding:0;">
  <tr>
    <td align="center" style="padding:24px 10px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; width:100%; background:#FFFFFF; border-radius:18px; overflow:hidden; box-shadow:0 12px 40px rgba(0,82,204,0.10);">

        <!-- Logo -->
        <tr>
          <td class="px hero" bgcolor="#FFFFFF" style="background:#FFFFFF; padding:38px 40px 30px 40px;" align="center">
            <img class="logo" src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-logo-horizontal-single-icon.png" width="300" alt="Etijahi · إتجاهي" style="display:block; width:300px; max-width:78%; height:auto; margin:0 auto 12px auto;">
            <p style="margin:0; color:#5a6a85;"><span style="font-family:Arial,Helvetica,sans-serif; font-size:10px;">by Etijah Coaching &amp; Consulting</span> &nbsp;·&nbsp; <span style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:10px;">من اتجاه للإرشاد والاستشارات</span></p>
          </td>
        </tr>

        <!-- Beta eyebrow bar -->
        <tr>
          <td class="px" bgcolor="#0052CC" style="background:#0052CC; padding:14px 40px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" class="eyebrow"><tr>
              <td width="50%" align="left" dir="ltr" style="font-family:Arial,Helvetica,sans-serif; font-size:13px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:#FFFFFF; padding-right:16px; white-space:nowrap;">Private beta · Closing soon</td>
              <td width="50%" align="right" dir="rtl" style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:15px; font-weight:bold; color:#FFFFFF;">النسخة التجريبية تُغلق قريباً</td>
            </tr></table>
          </td>
        </tr>
        <tr><td style="height:4px; background:#00C9A7; font-size:0; line-height:0;">&nbsp;</td></tr>

        <!-- ================= ARABIC ================= -->
        <tr>
          <td class="px" dir="rtl" align="right" style="padding:34px 40px 0 40px; font-family:'Segoe UI',Tahoma,Arial,sans-serif;">
            <p class="herotitle" style="margin:0 0 22px 0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:30px; line-height:1.5; font-weight:bold; color:#0052CC;">مقعدك في إتجاهي ما زال محجوزاً</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">عزيزي/عزيزتي {{first_name}}،</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">مقعدك في النسخة التجريبية من إتجاهي <strong style="color:#0052CC;">ما زال محجوزاً</strong>.</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">خمس عشرة دقيقة فقط. وإن كنت تنتظر وقتاً هادئاً مناسباً، فهذا تذكير بأن ذلك الوقت نادراً ما يأتي وحده.</p>
            <p style="margin:0 0 22px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">اختبار الـBeta سيُغلق قريباً، وهذه فرصتك لتجربة إتجاهي قبل إغلاقه. وبعد تجربتك، نود أن تشاركنا رأيك وملاحظاتك بكل صراحة، فهي تساعدنا على تطوير التجربة بشكل أفضل.</p>
          </td>
        </tr>

        <!-- AR access card -->
        <tr><td class="px" dir="rtl" style="padding:0 40px 8px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td class="accesscard" align="center" bgcolor="#EBF3FF" style="background:#EBF3FF; border:1px solid #cfe0fb; border-radius:14px; padding:28px 26px;">
              <p style="margin:0 0 6px 0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:13px; font-weight:bold; letter-spacing:0.5px; color:#0052CC;">لا تفوّت الفرصة — ابدأ تقييمك الآن</p>
              <p dir="ltr" style="margin:0 0 20px 0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:1.7; color:#5a6a85; word-break:break-all;"><a href="https://myetijahi.com/ar/assessment" style="color:#0052CC; text-decoration:underline; font-weight:bold;">myetijahi.com/ar/assessment</a></p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:auto; margin:0 auto;" class="cta"><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius:40px;">
                  <a href="https://myetijahi.com/ar/assessment" style="display:inline-block; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:17px; font-weight:bold; color:#FFFFFF; text-decoration:none; padding:17px 46px; border-radius:40px;">&#8207;ابدأ تقييمك&nbsp;←</a>
                </td>
              </tr></table>
              <p style="margin:18px 0 0 0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:14px; line-height:1.8; color:#2D2D2D;">يستغرق التقييم حوالي <strong style="color:#0052CC;">15 دقيقة</strong>.</p>
            </td>
          </tr></table>
        </td></tr>

        <tr><td class="px" dir="rtl" align="right" style="padding:24px 40px 28px 40px; font-family:'Segoe UI',Tahoma,Arial,sans-serif;">
          <p style="margin:0; font-size:15px; line-height:1.9; color:#2D2D2D;">مع التقدير،<br><strong>فريق اتجاه للإرشاد و الاستشارات</strong></p>
        </td></tr>

        <!-- Divider -->
        <tr><td class="px" style="padding:6px 40px 28px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td width="44%" style="border-top:1px solid #dce7fb; font-size:0; line-height:0;">&nbsp;</td>
            <td width="12%" align="center" style="font-size:0; line-height:0;"><span style="display:inline-block; width:9px; height:9px; background:#00C9A7; border-radius:50%;">&nbsp;</span></td>
            <td width="44%" style="border-top:1px solid #dce7fb; font-size:0; line-height:0;">&nbsp;</td>
          </tr></table>
        </td></tr>

        <!-- ================= ENGLISH ================= -->
        <tr>
          <td class="px" dir="ltr" align="left" style="padding:0 40px 0 40px; font-family:Arial,Helvetica,sans-serif;">
            <p class="herotitle" style="margin:0 0 22px 0; font-family:Arial,Helvetica,sans-serif; font-size:30px; line-height:1.35; font-weight:bold; color:#0052CC;">Your place in Etijahi is still reserved</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">Dear {{first_name}},</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">Your place in the Etijahi private beta is <strong style="color:#0052CC;">still reserved</strong>.</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">Just fifteen minutes. And if you have been waiting for a quiet moment, this is a reminder that the right moment rarely arrives on its own.</p>
            <p style="margin:0 0 22px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">The beta test will be closing soon, so this is your opportunity to experience Etijahi before it closes. Once you’ve completed the assessment, we’d love to hear your honest feedback — it will help us make the experience even better.</p>
          </td>
        </tr>

        <!-- EN access card -->
        <tr><td class="px" dir="ltr" style="padding:0 40px 8px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td class="accesscard" align="center" bgcolor="#EBF3FF" style="background:#EBF3FF; border:1px solid #cfe0fb; border-radius:14px; padding:28px 26px;">
              <p style="margin:0 0 6px 0; font-family:Arial,Helvetica,sans-serif; font-size:12px; font-weight:bold; letter-spacing:1.2px; text-transform:uppercase; color:#0052CC;">Don’t miss the opportunity — start your assessment today</p>
              <p style="margin:0 0 20px 0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:1.7; color:#5a6a85; word-break:break-all;"><a href="https://myetijahi.com/en/assessment" style="color:#0052CC; text-decoration:underline; font-weight:bold;">myetijahi.com/en/assessment</a></p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:auto; margin:0 auto;" class="cta"><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius:40px;">
                  <a href="https://myetijahi.com/en/assessment" style="display:inline-block; font-family:Arial,Helvetica,sans-serif; font-size:17px; font-weight:bold; color:#FFFFFF; text-decoration:none; padding:17px 44px; border-radius:40px;">Start Your Assessment &nbsp;→</a>
                </td>
              </tr></table>
              <p style="margin:18px 0 0 0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:1.8; color:#2D2D2D;">The assessment takes about <strong style="color:#0052CC;">15 minutes</strong>.</p>
            </td>
          </tr></table>
        </td></tr>

        <tr><td class="px" dir="ltr" align="left" style="padding:24px 40px 28px 40px; font-family:Arial,Helvetica,sans-serif;">
          <p style="margin:0; font-size:15px; line-height:1.9; color:#2D2D2D;">With regards,<br><strong>Etijah Coaching &amp; Consulting Team</strong></p>
        </td></tr>

        <!-- ================= SUPPORT ================= -->
        <tr><td class="px" style="padding:0 40px 30px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td style="background:#F5F9FF; border-top:3px solid #0052CC; border-radius:14px; padding:24px 24px 18px 24px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr"><tr>
                <td width="50%" align="left" dir="ltr" style="font-family:Arial,Helvetica,sans-serif; font-size:15px; font-weight:bold; color:#0052CC; padding-bottom:6px; padding-right:16px;">Need help?</td>
                <td width="50%" align="right" dir="rtl" style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:15px; font-weight:bold; color:#0052CC; padding-bottom:6px;">هل تحتاج مساعدة؟</td>
              </tr><tr>
                <td width="50%" align="left" dir="ltr" style="font-family:Arial,Helvetica,sans-serif; font-size:13px; line-height:1.9; color:#5a6a85; padding-bottom:16px; padding-right:16px;">For any question or technical issue: reply to this email, or reach us on WhatsApp or by phone.</td>
                <td width="50%" align="right" dir="rtl" style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:13px; line-height:1.9; color:#5a6a85; padding-bottom:16px;">لأي سؤال أو مشكلة تقنية: يكفي الرد على هذه الرسالة، أو تواصل معنا عبر واتساب أو الهاتف.</td>
              </tr></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr"><tr>
                <td class="support-col" width="50%" align="center" valign="top" style="padding:0 8px 0 0;">
                  <p style="margin:0 0 4px 0; font-family:Arial,Helvetica,sans-serif; font-size:11px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:#5a6a85;">Saudi Arabia &nbsp;·&nbsp; <span style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; letter-spacing:0;">السعودية</span></p>
                  <p style="margin:0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:2.1;"><a dir="ltr" href="https://wa.me/966550770711" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">+966 55 077 0711</a></p>
                </td>
                <td class="support-col" width="50%" align="center" valign="top" style="padding:0 0 0 8px;">
                  <p style="margin:0 0 4px 0; font-family:Arial,Helvetica,sans-serif; font-size:11px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:#5a6a85;">Bahrain &nbsp;·&nbsp; <span style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; letter-spacing:0;">البحرين</span></p>
                  <p style="margin:0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:2.1;"><a dir="ltr" href="https://wa.me/97333462820" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">+973 3346 2820</a></p>
                </td>
              </tr></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
                <td align="center" style="border-top:1px solid #dce7fb; padding-top:14px; font-family:Arial,Helvetica,sans-serif; font-size:13px; line-height:2.1;">
                  <a dir="ltr" href="mailto:info@myetijahi.com" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-email.png" width="16" height="16" alt="Email" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">info@myetijahi.com</a>&nbsp;&nbsp;&nbsp;&nbsp;<a dir="ltr" href="https://etijahcoaching.com/" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-website.png" width="16" height="16" alt="Website" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">etijahcoaching.com</a>
                </td>
              </tr></table>
            </td>
          </tr></table>
        </td></tr>

        <!-- Footer -->
        <tr>
          <td class="px" bgcolor="#00C9A7" style="background:#00C9A7; padding:26px 40px;" align="center">
            <p style="margin:0 0 4px 0; font-family:Arial,Helvetica,sans-serif; font-size:12px; line-height:1.6; color:#FFFFFF; font-weight:bold;">Etijah Coaching &amp; Consulting</p>
            <p style="margin:0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:12px; line-height:1.6; color:#FFFFFF;">اتجاه للإرشاد والاستشارات</p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>
$body$,
$body$<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<!-- ============================================================
     ETIJAHI — Beta reminder ("your place is still reserved")
     SUBJECT (AR): مقعدك في إتجاهي ما زال محجوزاً
     SUBJECT (EN): Your place in Etijahi is still reserved
     Access links: AR https://myetijahi.com/ar/assessment
                   EN https://myetijahi.com/en/assessment
     Palette: #0052CC blue · #00C9A7 teal · #EBF3FF light ·
              #2D2D2D charcoal · #FFFFFF white.
     ============================================================ -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<title>Etijahi · مقعدك ما زال محجوزاً</title>
<style>
  body, table, td { -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }
  img { border:0; outline:none; text-decoration:none; -ms-interpolation-mode:bicubic; }
  a { text-decoration:none; }
  @media only screen and (max-width:620px) {
    .px       { padding-left:22px !important; padding-right:22px !important; }
    .hero     { padding-top:30px !important; padding-bottom:22px !important; }
    .logo     { width:240px !important; max-width:70% !important; }
    .cta a    { display:block !important; padding-left:20px !important; padding-right:20px !important; }
    .eyebrow td { font-size:11px !important; letter-spacing:0.5px !important; }
    .callout  { padding:16px 16px !important; }
    .accesscard { padding:22px 18px !important; }
    .herotitle { font-size:26px !important; }
    .support-col { display:block !important; width:100% !important; padding:0 0 14px 0 !important; }
  }
</style>
</head>
<body style="margin:0; padding:0; background:#EBF3FF;">
<span style="display:none; font-size:0; line-height:0; max-height:0; opacity:0; overflow:hidden; mso-hide:all;">خمس عشرة دقيقة فقط، واختبار الـBeta سيُغلق قريباً · Just fifteen minutes — the beta closes soon.</span>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#EBF3FF; margin:0; padding:0;">
  <tr>
    <td align="center" style="padding:24px 10px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; width:100%; background:#FFFFFF; border-radius:18px; overflow:hidden; box-shadow:0 12px 40px rgba(0,82,204,0.10);">

        <!-- Logo -->
        <tr>
          <td class="px hero" bgcolor="#FFFFFF" style="background:#FFFFFF; padding:38px 40px 30px 40px;" align="center">
            <img class="logo" src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-logo-horizontal-single-icon.png" width="300" alt="Etijahi · إتجاهي" style="display:block; width:300px; max-width:78%; height:auto; margin:0 auto 12px auto;">
            <p style="margin:0; color:#5a6a85;"><span style="font-family:Arial,Helvetica,sans-serif; font-size:10px;">by Etijah Coaching &amp; Consulting</span> &nbsp;·&nbsp; <span style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:10px;">من اتجاه للإرشاد والاستشارات</span></p>
          </td>
        </tr>

        <!-- Beta eyebrow bar -->
        <tr>
          <td class="px" bgcolor="#0052CC" style="background:#0052CC; padding:14px 40px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" class="eyebrow"><tr>
              <td width="50%" align="left" dir="ltr" style="font-family:Arial,Helvetica,sans-serif; font-size:13px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:#FFFFFF; padding-right:16px; white-space:nowrap;">Private beta · Closing soon</td>
              <td width="50%" align="right" dir="rtl" style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:15px; font-weight:bold; color:#FFFFFF;">النسخة التجريبية تُغلق قريباً</td>
            </tr></table>
          </td>
        </tr>
        <tr><td style="height:4px; background:#00C9A7; font-size:0; line-height:0;">&nbsp;</td></tr>

        <!-- ================= ARABIC ================= -->
        <tr>
          <td class="px" dir="rtl" align="right" style="padding:34px 40px 0 40px; font-family:'Segoe UI',Tahoma,Arial,sans-serif;">
            <p class="herotitle" style="margin:0 0 22px 0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:30px; line-height:1.5; font-weight:bold; color:#0052CC;">مقعدك في إتجاهي ما زال محجوزاً</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">عزيزي/عزيزتي {{first_name}}،</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">مقعدك في النسخة التجريبية من إتجاهي <strong style="color:#0052CC;">ما زال محجوزاً</strong>.</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">خمس عشرة دقيقة فقط. وإن كنت تنتظر وقتاً هادئاً مناسباً، فهذا تذكير بأن ذلك الوقت نادراً ما يأتي وحده.</p>
            <p style="margin:0 0 22px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">اختبار الـBeta سيُغلق قريباً، وهذه فرصتك لتجربة إتجاهي قبل إغلاقه. وبعد تجربتك، نود أن تشاركنا رأيك وملاحظاتك بكل صراحة، فهي تساعدنا على تطوير التجربة بشكل أفضل.</p>
          </td>
        </tr>

        <!-- AR access card -->
        <tr><td class="px" dir="rtl" style="padding:0 40px 8px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td class="accesscard" align="center" bgcolor="#EBF3FF" style="background:#EBF3FF; border:1px solid #cfe0fb; border-radius:14px; padding:28px 26px;">
              <p style="margin:0 0 6px 0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:13px; font-weight:bold; letter-spacing:0.5px; color:#0052CC;">لا تفوّت الفرصة — ابدأ تقييمك الآن</p>
              <p dir="ltr" style="margin:0 0 20px 0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:1.7; color:#5a6a85; word-break:break-all;"><a href="https://myetijahi.com/ar/assessment" style="color:#0052CC; text-decoration:underline; font-weight:bold;">myetijahi.com/ar/assessment</a></p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:auto; margin:0 auto;" class="cta"><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius:40px;">
                  <a href="https://myetijahi.com/ar/assessment" style="display:inline-block; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:17px; font-weight:bold; color:#FFFFFF; text-decoration:none; padding:17px 46px; border-radius:40px;">&#8207;ابدأ تقييمك&nbsp;←</a>
                </td>
              </tr></table>
              <p style="margin:18px 0 0 0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:14px; line-height:1.8; color:#2D2D2D;">يستغرق التقييم حوالي <strong style="color:#0052CC;">15 دقيقة</strong>.</p>
            </td>
          </tr></table>
        </td></tr>

        <tr><td class="px" dir="rtl" align="right" style="padding:24px 40px 28px 40px; font-family:'Segoe UI',Tahoma,Arial,sans-serif;">
          <p style="margin:0; font-size:15px; line-height:1.9; color:#2D2D2D;">مع التقدير،<br><strong>فريق اتجاه للإرشاد و الاستشارات</strong></p>
        </td></tr>

        <!-- Divider -->
        <tr><td class="px" style="padding:6px 40px 28px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td width="44%" style="border-top:1px solid #dce7fb; font-size:0; line-height:0;">&nbsp;</td>
            <td width="12%" align="center" style="font-size:0; line-height:0;"><span style="display:inline-block; width:9px; height:9px; background:#00C9A7; border-radius:50%;">&nbsp;</span></td>
            <td width="44%" style="border-top:1px solid #dce7fb; font-size:0; line-height:0;">&nbsp;</td>
          </tr></table>
        </td></tr>

        <!-- ================= ENGLISH ================= -->
        <tr>
          <td class="px" dir="ltr" align="left" style="padding:0 40px 0 40px; font-family:Arial,Helvetica,sans-serif;">
            <p class="herotitle" style="margin:0 0 22px 0; font-family:Arial,Helvetica,sans-serif; font-size:30px; line-height:1.35; font-weight:bold; color:#0052CC;">Your place in Etijahi is still reserved</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">Dear {{first_name}},</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">Your place in the Etijahi private beta is <strong style="color:#0052CC;">still reserved</strong>.</p>
            <p style="margin:0 0 16px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">Just fifteen minutes. And if you have been waiting for a quiet moment, this is a reminder that the right moment rarely arrives on its own.</p>
            <p style="margin:0 0 22px 0; font-size:15px; line-height:1.9; color:#2D2D2D;">The beta test will be closing soon, so this is your opportunity to experience Etijahi before it closes. Once you’ve completed the assessment, we’d love to hear your honest feedback — it will help us make the experience even better.</p>
          </td>
        </tr>

        <!-- EN access card -->
        <tr><td class="px" dir="ltr" style="padding:0 40px 8px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td class="accesscard" align="center" bgcolor="#EBF3FF" style="background:#EBF3FF; border:1px solid #cfe0fb; border-radius:14px; padding:28px 26px;">
              <p style="margin:0 0 6px 0; font-family:Arial,Helvetica,sans-serif; font-size:12px; font-weight:bold; letter-spacing:1.2px; text-transform:uppercase; color:#0052CC;">Don’t miss the opportunity — start your assessment today</p>
              <p style="margin:0 0 20px 0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:1.7; color:#5a6a85; word-break:break-all;"><a href="https://myetijahi.com/en/assessment" style="color:#0052CC; text-decoration:underline; font-weight:bold;">myetijahi.com/en/assessment</a></p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:auto; margin:0 auto;" class="cta"><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius:40px;">
                  <a href="https://myetijahi.com/en/assessment" style="display:inline-block; font-family:Arial,Helvetica,sans-serif; font-size:17px; font-weight:bold; color:#FFFFFF; text-decoration:none; padding:17px 44px; border-radius:40px;">Start Your Assessment &nbsp;→</a>
                </td>
              </tr></table>
              <p style="margin:18px 0 0 0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:1.8; color:#2D2D2D;">The assessment takes about <strong style="color:#0052CC;">15 minutes</strong>.</p>
            </td>
          </tr></table>
        </td></tr>

        <tr><td class="px" dir="ltr" align="left" style="padding:24px 40px 28px 40px; font-family:Arial,Helvetica,sans-serif;">
          <p style="margin:0; font-size:15px; line-height:1.9; color:#2D2D2D;">With regards,<br><strong>Etijah Coaching &amp; Consulting Team</strong></p>
        </td></tr>

        <!-- ================= SUPPORT ================= -->
        <tr><td class="px" style="padding:0 40px 30px 40px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td style="background:#F5F9FF; border-top:3px solid #0052CC; border-radius:14px; padding:24px 24px 18px 24px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr"><tr>
                <td width="50%" align="left" dir="ltr" style="font-family:Arial,Helvetica,sans-serif; font-size:15px; font-weight:bold; color:#0052CC; padding-bottom:6px; padding-right:16px;">Need help?</td>
                <td width="50%" align="right" dir="rtl" style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:15px; font-weight:bold; color:#0052CC; padding-bottom:6px;">هل تحتاج مساعدة؟</td>
              </tr><tr>
                <td width="50%" align="left" dir="ltr" style="font-family:Arial,Helvetica,sans-serif; font-size:13px; line-height:1.9; color:#5a6a85; padding-bottom:16px; padding-right:16px;">For any question or technical issue: reply to this email, or reach us on WhatsApp or by phone.</td>
                <td width="50%" align="right" dir="rtl" style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:13px; line-height:1.9; color:#5a6a85; padding-bottom:16px;">لأي سؤال أو مشكلة تقنية: يكفي الرد على هذه الرسالة، أو تواصل معنا عبر واتساب أو الهاتف.</td>
              </tr></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr"><tr>
                <td class="support-col" width="50%" align="center" valign="top" style="padding:0 8px 0 0;">
                  <p style="margin:0 0 4px 0; font-family:Arial,Helvetica,sans-serif; font-size:11px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:#5a6a85;">Saudi Arabia &nbsp;·&nbsp; <span style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; letter-spacing:0;">السعودية</span></p>
                  <p style="margin:0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:2.1;"><a dir="ltr" href="https://wa.me/966550770711" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">+966 55 077 0711</a></p>
                </td>
                <td class="support-col" width="50%" align="center" valign="top" style="padding:0 0 0 8px;">
                  <p style="margin:0 0 4px 0; font-family:Arial,Helvetica,sans-serif; font-size:11px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:#5a6a85;">Bahrain &nbsp;·&nbsp; <span style="font-family:'Segoe UI',Tahoma,Arial,sans-serif; letter-spacing:0;">البحرين</span></p>
                  <p style="margin:0; font-family:Arial,Helvetica,sans-serif; font-size:14px; line-height:2.1;"><a dir="ltr" href="https://wa.me/97333462820" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">+973 3346 2820</a></p>
                </td>
              </tr></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
                <td align="center" style="border-top:1px solid #dce7fb; padding-top:14px; font-family:Arial,Helvetica,sans-serif; font-size:13px; line-height:2.1;">
                  <a dir="ltr" href="mailto:info@myetijahi.com" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-email.png" width="16" height="16" alt="Email" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">info@myetijahi.com</a>&nbsp;&nbsp;&nbsp;&nbsp;<a dir="ltr" href="https://etijahcoaching.com/" style="color:#0052CC; text-decoration:none; font-weight:bold; white-space:nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-website.png" width="16" height="16" alt="Website" style="width:16px; height:16px; vertical-align:middle; margin:0 6px 3px 0;">etijahcoaching.com</a>
                </td>
              </tr></table>
            </td>
          </tr></table>
        </td></tr>

        <!-- Footer -->
        <tr>
          <td class="px" bgcolor="#00C9A7" style="background:#00C9A7; padding:26px 40px;" align="center">
            <p style="margin:0 0 4px 0; font-family:Arial,Helvetica,sans-serif; font-size:12px; line-height:1.6; color:#FFFFFF; font-weight:bold;">Etijah Coaching &amp; Consulting</p>
            <p style="margin:0; font-family:'Segoe UI',Tahoma,Arial,sans-serif; font-size:12px; line-height:1.6; color:#FFFFFF;">اتجاه للإرشاد والاستشارات</p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>
$body$,
 '["first_name"]'::jsonb
)
on conflict (key) do nothing;
