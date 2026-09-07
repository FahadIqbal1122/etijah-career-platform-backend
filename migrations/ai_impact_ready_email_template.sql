insert into email_templates (key, name, description, is_active, subject_en, subject_ar, body_html_en, body_html_ar, variables) values
('ai_impact_ready', 'AI Impact Analysis Ready (backfill re-engagement)', 'One-off bilingual email to assessment takers whose AI Career Impact section failed to generate due to a provider misconfiguration; sent once it was fixed and backfilled, inviting them to revisit their results and, optionally, update their feedback. Both languages are in a single email body (like beta_invite) so body_html_en and body_html_ar are identical.', true,
 'Your AI Career Impact Analysis Is Ready · تحليل تأثير الذكاء الاصطناعي على مسارك المهني جاهز الآن',
 'Your AI Career Impact Analysis Is Ready · تحليل تأثير الذكاء الاصطناعي على مسارك المهني جاهز الآن',
'<br><span style="display: none; font-size: 0px; line-height: 0; max-height: 0px; opacity: 0; overflow: hidden;">تم إصلاح مشكلة تحليل تأثير الذكاء الاصطناعي في تقريرك · There was an issue with your AI Career Impact analysis — it''s fixed now.</span>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background: rgb(235, 243, 255); margin: 0px; padding: 0px; text-size-adjust: 100%;">
  <tbody><tr>
    <td align="center" style="padding: 24px 10px; text-size-adjust: 100%;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background: rgb(255, 255, 255); border-radius: 18px; overflow: hidden; box-shadow: rgba(0, 82, 204, 0.1) 0px 12px 40px; text-size-adjust: 100%;">

        <tbody><tr>
          <td bgcolor="#FFFFFF" style="background: rgb(255, 255, 255); padding: 38px 40px 30px; text-size-adjust: 100%;" align="center">
            <img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-logo-horizontal-single-icon.png" width="300" alt="Etijahi · إتجاهي" style="display: block; width: 300px; max-width: 78%; height: auto; margin: 0px auto 12px; border: 0px; outline: none; text-decoration: none;">
            <p style="margin: 0px; color: rgb(90, 106, 133);"><span style="font-family: Arial, Helvetica, sans-serif; font-size: 10px;">by Etijah Coaching &amp; Consulting</span> &nbsp;·&nbsp; <span style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 10px;">من اتجاه للإرشاد والاستشارات</span></p>
          </td>
        </tr>

        <tr>
          <td bgcolor="#0052CC" style="background: rgb(0, 82, 204); padding: 14px 40px; text-size-adjust: 100%;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
              <td width="50%" align="left" dir="ltr" style="font-family: Arial, Helvetica, sans-serif; font-size: 13px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; color: rgb(255, 255, 255); padding-right: 16px; text-size-adjust: 100%;">Report update · AI Career Impact</td>
              <td width="50%" align="right" dir="rtl" style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 15px; font-weight: bold; color: rgb(255, 255, 255); text-size-adjust: 100%;">تحديث على تقريرك · تأثير الذكاء الاصطناعي</td>
            </tr></tbody></table>
          </td>
        </tr>
        <tr><td style="height: 4px; background: rgb(0, 201, 167); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td></tr>

        <tr>
          <td dir="rtl" align="right" style="padding: 34px 40px 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; text-size-adjust: 100%;">
            <p style="margin: 0px 0px 22px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 26px; line-height: 1.5; font-weight: bold; color: rgb(0, 82, 204);">تحليل تأثير الذكاء الاصطناعي على مسارك المهني جاهز الآن</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">مرحباً {{full_name}}،</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">كانت هناك مشكلة في قسم <strong style="color: rgb(0, 82, 204);">تأثير الذكاء الاصطناعي</strong> ضمن تقريرك — لم يظهر تحليل تأثير الذكاء الاصطناعي على أبرز المسارات المهنية المطابقة لك بشكل صحيح، بسبب مشكلة تقنية من جانبنا.</p>
            <p style="margin: 0px 0px 22px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">تم إصلاح المشكلة الآن، وتحليلك الشخصي — بما يشمل مستوى التأثير المتوقع، والمهام الأكثر عرضة للتأثر، والمهارات التي تحميك — جاهز الآن. يمكنك مراجعة تقريرك مرة أخرى أدناه.</p>
          </td>
        </tr>

        <tr><td dir="rtl" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" bgcolor="#EBF3FF" style="background: rgb(235, 243, 255); border: 1px solid rgb(207, 224, 251); border-radius: 14px; padding: 28px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 20px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">لا داعي لإعادة أي شيء — فقط راجع النتائج التي حصلت عليها سابقاً.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{results_url}}" style="display: inline-block; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 17px; font-weight: bold; color: rgb(255, 255, 255); text-decoration: none; padding: 17px 46px; border-radius: 40px;">‏راجع تقريرك مرة أخرى&nbsp;←</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="rtl" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" style="border: 1px solid rgb(220, 231, 251); border-radius: 14px; padding: 22px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 16px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">سبق أن أرسلت لنا ملاحظاتك؟ يمكنك الرجوع وتعديلها إذا أردت.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border: 2px solid rgb(0, 82, 204); border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{feedback_url}}" style="display: inline-block; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); text-decoration: none; padding: 13px 34px; border-radius: 40px;">‏تعديل ملاحظاتك&nbsp;←</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="rtl" align="right" style="padding: 22px 40px 8px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; text-size-adjust: 100%;">
          <p style="margin: 0px 0px 16px; font-size: 14px; line-height: 1.9; color: rgb(90, 106, 133);">نعتذر عن الإزعاج، وإذا كان لديك أي سؤال، يكفي الرد على هذه الرسالة.</p>
          <p style="margin: 0px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">مع خالص التقدير،<br><strong>فريق اتجاه للإرشاد والاستشارات</strong></p>
        </td></tr>

        <tr><td style="padding: 6px 40px 28px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td width="44%" style="border-top: 1px solid rgb(220, 231, 251); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td>
            <td width="12%" align="center" style="font-size: 0px; line-height: 0; text-size-adjust: 100%;"><span style="display: inline-block; width: 9px; height: 9px; background: rgb(0, 201, 167); border-radius: 50%;">&nbsp;</span></td>
            <td width="44%" style="border-top: 1px solid rgb(220, 231, 251); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td>
          </tr></tbody></table>
        </td></tr>

        <tr>
          <td dir="ltr" align="left" style="padding: 0px 40px; font-family: Arial, Helvetica, sans-serif; text-size-adjust: 100%;">
            <p style="margin: 0px 0px 22px; font-family: Arial, Helvetica, sans-serif; font-size: 28px; line-height: 1.35; font-weight: bold; color: rgb(0, 82, 204);">Your AI Career Impact Analysis Is Ready</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">Hi {{full_name}},</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">There was an issue with the <strong style="color: rgb(0, 82, 204);">AI Career Impact</strong> section of your report &mdash; the analysis of AI&rsquo;s impact on your top matched careers didn&rsquo;t generate correctly because of a technical issue on our end.</p>
            <p style="margin: 0px 0px 22px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">It&rsquo;s fixed now, and your personalized analysis &mdash; including AI risk level, at-risk tasks, and the skills that keep you protected &mdash; is ready and waiting. You can check your report again below.</p>
          </td>
        </tr>

        <tr><td dir="ltr" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" bgcolor="#EBF3FF" style="background: rgb(235, 243, 255); border: 1px solid rgb(207, 224, 251); border-radius: 14px; padding: 28px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 20px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">No need to retake anything &mdash; just check the results you already have.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{results_url}}" style="display: inline-block; font-family: Arial, Helvetica, sans-serif; font-size: 17px; font-weight: bold; color: rgb(255, 255, 255); text-decoration: none; padding: 17px 44px; border-radius: 40px;">Check Your Report Again &nbsp;&rarr;</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="ltr" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" style="border: 1px solid rgb(220, 231, 251); border-radius: 14px; padding: 22px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 16px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">Already sent us feedback? You can still go back and update it if you&rsquo;d like.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border: 2px solid rgb(0, 82, 204); border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{feedback_url}}" style="display: inline-block; font-family: Arial, Helvetica, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); text-decoration: none; padding: 13px 36px; border-radius: 40px;">Update Your Feedback &nbsp;&rarr;</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="ltr" align="left" style="padding: 22px 40px 28px; font-family: Arial, Helvetica, sans-serif; text-size-adjust: 100%;">
          <p style="margin: 0px 0px 16px; font-size: 14px; line-height: 1.9; color: rgb(90, 106, 133);">Sorry for the inconvenience &mdash; if you have any questions, simply reply to this email.</p>
          <p style="margin: 0px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">With regards,<br><strong>Etijah Coaching &amp; Consulting Team</strong></p>
        </td></tr>

        <tr><td style="padding: 0px 40px 30px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td style="background: rgb(245, 249, 255); border-top: 3px solid rgb(0, 82, 204); border-radius: 14px; padding: 24px 24px 18px; text-size-adjust: 100%;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
                <td width="50%" align="left" dir="ltr" style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); padding-bottom: 6px; padding-right: 16px; text-size-adjust: 100%;">Need help?</td>
                <td width="50%" align="right" dir="rtl" style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); padding-bottom: 6px; text-size-adjust: 100%;">هل تحتاج مساعدة؟</td>
              </tr><tr>
                <td width="50%" align="left" dir="ltr" style="font-family: Arial, Helvetica, sans-serif; font-size: 13px; line-height: 1.9; color: rgb(90, 106, 133); padding-bottom: 16px; padding-right: 16px; text-size-adjust: 100%;">For any question or technical issue: reply to this email, or reach us on WhatsApp or by phone.</td>
                <td width="50%" align="right" dir="rtl" style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 13px; line-height: 1.9; color: rgb(90, 106, 133); padding-bottom: 16px; text-size-adjust: 100%;">لأي سؤال أو مشكلة تقنية: يكفي الرد على هذه الرسالة، أو تواصل معنا عبر واتساب أو الهاتف.</td>
              </tr></tbody></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
                <td width="50%" align="center" valign="top" style="padding: 0px 8px 0px 0px; text-size-adjust: 100%;">
                  <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: rgb(90, 106, 133);">Saudi Arabia &nbsp;·&nbsp; <span style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; letter-spacing: 0px;">السعودية</span></p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/966550770711" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+966 55 077 0711</a></p>
                </td>
                <td width="50%" align="center" valign="top" style="padding: 0px 0px 0px 8px; text-size-adjust: 100%;">
                  <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: rgb(90, 106, 133);">Bahrain &nbsp;·&nbsp; <span style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; letter-spacing: 0px;">البحرين</span></p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/97333462820" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+973 3346 2820</a></p>
                </td>
              </tr></tbody></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 16px; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border-top: 1px solid rgb(220, 231, 251); padding-top: 14px; font-family: Arial, Helvetica, sans-serif; font-size: 13px; line-height: 2.1; text-size-adjust: 100%;">
                  <a dir="ltr" href="mailto:info@myetijahi.com" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-email.png" width="16" height="16" alt="Email" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">info@myetijahi.com</a>&nbsp;&nbsp;&nbsp;&nbsp;<a dir="ltr" href="https://etijahcoaching.com/" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-website.png" width="16" height="16" alt="Website" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">etijahcoaching.com</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr>
          <td bgcolor="#00C9A7" style="background: rgb(0, 201, 167); padding: 26px 40px; text-size-adjust: 100%;" align="center">
            <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255); font-weight: bold;">Etijah Coaching &amp; Consulting</p>
            <p style="margin: 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255);">اتجاه للإرشاد والاستشارات</p>
          </td>
        </tr>

      </tbody></table>
    </td>
  </tr>
</tbody></table>',
'<br><span style="display: none; font-size: 0px; line-height: 0; max-height: 0px; opacity: 0; overflow: hidden;">تم إصلاح مشكلة تحليل تأثير الذكاء الاصطناعي في تقريرك · There was an issue with your AI Career Impact analysis — it''s fixed now.</span>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background: rgb(235, 243, 255); margin: 0px; padding: 0px; text-size-adjust: 100%;">
  <tbody><tr>
    <td align="center" style="padding: 24px 10px; text-size-adjust: 100%;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background: rgb(255, 255, 255); border-radius: 18px; overflow: hidden; box-shadow: rgba(0, 82, 204, 0.1) 0px 12px 40px; text-size-adjust: 100%;">

        <tbody><tr>
          <td bgcolor="#FFFFFF" style="background: rgb(255, 255, 255); padding: 38px 40px 30px; text-size-adjust: 100%;" align="center">
            <img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-logo-horizontal-single-icon.png" width="300" alt="Etijahi · إتجاهي" style="display: block; width: 300px; max-width: 78%; height: auto; margin: 0px auto 12px; border: 0px; outline: none; text-decoration: none;">
            <p style="margin: 0px; color: rgb(90, 106, 133);"><span style="font-family: Arial, Helvetica, sans-serif; font-size: 10px;">by Etijah Coaching &amp; Consulting</span> &nbsp;·&nbsp; <span style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 10px;">من اتجاه للإرشاد والاستشارات</span></p>
          </td>
        </tr>

        <tr>
          <td bgcolor="#0052CC" style="background: rgb(0, 82, 204); padding: 14px 40px; text-size-adjust: 100%;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
              <td width="50%" align="left" dir="ltr" style="font-family: Arial, Helvetica, sans-serif; font-size: 13px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; color: rgb(255, 255, 255); padding-right: 16px; text-size-adjust: 100%;">Report update · AI Career Impact</td>
              <td width="50%" align="right" dir="rtl" style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 15px; font-weight: bold; color: rgb(255, 255, 255); text-size-adjust: 100%;">تحديث على تقريرك · تأثير الذكاء الاصطناعي</td>
            </tr></tbody></table>
          </td>
        </tr>
        <tr><td style="height: 4px; background: rgb(0, 201, 167); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td></tr>

        <tr>
          <td dir="rtl" align="right" style="padding: 34px 40px 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; text-size-adjust: 100%;">
            <p style="margin: 0px 0px 22px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 26px; line-height: 1.5; font-weight: bold; color: rgb(0, 82, 204);">تحليل تأثير الذكاء الاصطناعي على مسارك المهني جاهز الآن</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">مرحباً {{full_name}}،</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">كانت هناك مشكلة في قسم <strong style="color: rgb(0, 82, 204);">تأثير الذكاء الاصطناعي</strong> ضمن تقريرك — لم يظهر تحليل تأثير الذكاء الاصطناعي على أبرز المسارات المهنية المطابقة لك بشكل صحيح، بسبب مشكلة تقنية من جانبنا.</p>
            <p style="margin: 0px 0px 22px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">تم إصلاح المشكلة الآن، وتحليلك الشخصي — بما يشمل مستوى التأثير المتوقع، والمهام الأكثر عرضة للتأثر، والمهارات التي تحميك — جاهز الآن. يمكنك مراجعة تقريرك مرة أخرى أدناه.</p>
          </td>
        </tr>

        <tr><td dir="rtl" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" bgcolor="#EBF3FF" style="background: rgb(235, 243, 255); border: 1px solid rgb(207, 224, 251); border-radius: 14px; padding: 28px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 20px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">لا داعي لإعادة أي شيء — فقط راجع النتائج التي حصلت عليها سابقاً.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{results_url}}" style="display: inline-block; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 17px; font-weight: bold; color: rgb(255, 255, 255); text-decoration: none; padding: 17px 46px; border-radius: 40px;">‏راجع تقريرك مرة أخرى&nbsp;←</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="rtl" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" style="border: 1px solid rgb(220, 231, 251); border-radius: 14px; padding: 22px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 16px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">سبق أن أرسلت لنا ملاحظاتك؟ يمكنك الرجوع وتعديلها إذا أردت.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border: 2px solid rgb(0, 82, 204); border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{feedback_url}}" style="display: inline-block; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); text-decoration: none; padding: 13px 34px; border-radius: 40px;">‏تعديل ملاحظاتك&nbsp;←</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="rtl" align="right" style="padding: 22px 40px 8px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; text-size-adjust: 100%;">
          <p style="margin: 0px 0px 16px; font-size: 14px; line-height: 1.9; color: rgb(90, 106, 133);">نعتذر عن الإزعاج، وإذا كان لديك أي سؤال، يكفي الرد على هذه الرسالة.</p>
          <p style="margin: 0px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">مع خالص التقدير،<br><strong>فريق اتجاه للإرشاد والاستشارات</strong></p>
        </td></tr>

        <tr><td style="padding: 6px 40px 28px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td width="44%" style="border-top: 1px solid rgb(220, 231, 251); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td>
            <td width="12%" align="center" style="font-size: 0px; line-height: 0; text-size-adjust: 100%;"><span style="display: inline-block; width: 9px; height: 9px; background: rgb(0, 201, 167); border-radius: 50%;">&nbsp;</span></td>
            <td width="44%" style="border-top: 1px solid rgb(220, 231, 251); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td>
          </tr></tbody></table>
        </td></tr>

        <tr>
          <td dir="ltr" align="left" style="padding: 0px 40px; font-family: Arial, Helvetica, sans-serif; text-size-adjust: 100%;">
            <p style="margin: 0px 0px 22px; font-family: Arial, Helvetica, sans-serif; font-size: 28px; line-height: 1.35; font-weight: bold; color: rgb(0, 82, 204);">Your AI Career Impact Analysis Is Ready</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">Hi {{full_name}},</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">There was an issue with the <strong style="color: rgb(0, 82, 204);">AI Career Impact</strong> section of your report &mdash; the analysis of AI&rsquo;s impact on your top matched careers didn&rsquo;t generate correctly because of a technical issue on our end.</p>
            <p style="margin: 0px 0px 22px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">It&rsquo;s fixed now, and your personalized analysis &mdash; including AI risk level, at-risk tasks, and the skills that keep you protected &mdash; is ready and waiting. You can check your report again below.</p>
          </td>
        </tr>

        <tr><td dir="ltr" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" bgcolor="#EBF3FF" style="background: rgb(235, 243, 255); border: 1px solid rgb(207, 224, 251); border-radius: 14px; padding: 28px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 20px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">No need to retake anything &mdash; just check the results you already have.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{results_url}}" style="display: inline-block; font-family: Arial, Helvetica, sans-serif; font-size: 17px; font-weight: bold; color: rgb(255, 255, 255); text-decoration: none; padding: 17px 44px; border-radius: 40px;">Check Your Report Again &nbsp;&rarr;</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="ltr" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" style="border: 1px solid rgb(220, 231, 251); border-radius: 14px; padding: 22px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 16px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">Already sent us feedback? You can still go back and update it if you&rsquo;d like.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border: 2px solid rgb(0, 82, 204); border-radius: 40px; text-size-adjust: 100%;">
                  <a href="{{feedback_url}}" style="display: inline-block; font-family: Arial, Helvetica, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); text-decoration: none; padding: 13px 36px; border-radius: 40px;">Update Your Feedback &nbsp;&rarr;</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="ltr" align="left" style="padding: 22px 40px 28px; font-family: Arial, Helvetica, sans-serif; text-size-adjust: 100%;">
          <p style="margin: 0px 0px 16px; font-size: 14px; line-height: 1.9; color: rgb(90, 106, 133);">Sorry for the inconvenience &mdash; if you have any questions, simply reply to this email.</p>
          <p style="margin: 0px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">With regards,<br><strong>Etijah Coaching &amp; Consulting Team</strong></p>
        </td></tr>

        <tr><td style="padding: 0px 40px 30px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td style="background: rgb(245, 249, 255); border-top: 3px solid rgb(0, 82, 204); border-radius: 14px; padding: 24px 24px 18px; text-size-adjust: 100%;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
                <td width="50%" align="left" dir="ltr" style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); padding-bottom: 6px; padding-right: 16px; text-size-adjust: 100%;">Need help?</td>
                <td width="50%" align="right" dir="rtl" style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 15px; font-weight: bold; color: rgb(0, 82, 204); padding-bottom: 6px; text-size-adjust: 100%;">هل تحتاج مساعدة؟</td>
              </tr><tr>
                <td width="50%" align="left" dir="ltr" style="font-family: Arial, Helvetica, sans-serif; font-size: 13px; line-height: 1.9; color: rgb(90, 106, 133); padding-bottom: 16px; padding-right: 16px; text-size-adjust: 100%;">For any question or technical issue: reply to this email, or reach us on WhatsApp or by phone.</td>
                <td width="50%" align="right" dir="rtl" style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 13px; line-height: 1.9; color: rgb(90, 106, 133); padding-bottom: 16px; text-size-adjust: 100%;">لأي سؤال أو مشكلة تقنية: يكفي الرد على هذه الرسالة، أو تواصل معنا عبر واتساب أو الهاتف.</td>
              </tr></tbody></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
                <td width="50%" align="center" valign="top" style="padding: 0px 8px 0px 0px; text-size-adjust: 100%;">
                  <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: rgb(90, 106, 133);">Saudi Arabia &nbsp;·&nbsp; <span style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; letter-spacing: 0px;">السعودية</span></p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/966550770711" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+966 55 077 0711</a></p>
                </td>
                <td width="50%" align="center" valign="top" style="padding: 0px 0px 0px 8px; text-size-adjust: 100%;">
                  <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: rgb(90, 106, 133);">Bahrain &nbsp;·&nbsp; <span style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; letter-spacing: 0px;">البحرين</span></p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/97333462820" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+973 3346 2820</a></p>
                </td>
              </tr></tbody></table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 16px; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border-top: 1px solid rgb(220, 231, 251); padding-top: 14px; font-family: Arial, Helvetica, sans-serif; font-size: 13px; line-height: 2.1; text-size-adjust: 100%;">
                  <a dir="ltr" href="mailto:info@myetijahi.com" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-email.png" width="16" height="16" alt="Email" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">info@myetijahi.com</a>&nbsp;&nbsp;&nbsp;&nbsp;<a dir="ltr" href="https://etijahcoaching.com/" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-website.png" width="16" height="16" alt="Website" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">etijahcoaching.com</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr>
          <td bgcolor="#00C9A7" style="background: rgb(0, 201, 167); padding: 26px 40px; text-size-adjust: 100%;" align="center">
            <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255); font-weight: bold;">Etijah Coaching &amp; Consulting</p>
            <p style="margin: 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255);">اتجاه للإرشاد والاستشارات</p>
          </td>
        </tr>

      </tbody></table>
    </td>
  </tr>
</tbody></table>',
 '["full_name", "results_url", "feedback_url"]'::jsonb
)
on conflict (key) do nothing;
